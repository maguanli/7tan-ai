"""
Agent 核心循环 — LLM 推理 + 工具调用 + 多步执行
详见架构文档 §5-7
"""
import json
import time
from datetime import datetime

from loguru import logger

from .model_manager import get_model
from .context_manager import ContextManager
from ..tools.registry import execute_tool, get_all_tools, get_tool
from ..tools.monitor_tools import track_cost
from ..database.db import get_session, ConversationHistory

# 最大迭代次数（防止无限循环）
MAX_ITERATIONS = 50


def _get_active_ai_config(config: dict) -> dict:
    """从多配置 AI 中获取当前活跃配置（兼容新旧格式）"""
    ai = config.get("ai", {})
    # 新格式：{active: "xxx", configs: {...}}
    if "configs" in ai:
        active_key = ai.get("active", "deepseek")
        return ai["configs"].get(active_key, {})
    # 旧格式：{provider: "xxx", model: "xxx", ...}
    return ai


def run_agent_loop(
    task: str,
    session_id: str = None,
    model_name: str = None,
    max_iterations: int = MAX_ITERATIONS,
) -> dict:
    """
    执行 Agent 循环 — ReAct 模式

    Args:
        task: 用户任务描述
        session_id: 会话 ID（用于对话历史）
        model_name: 指定模型（默认使用配置中的默认模型）
        max_iterations: 最大推理-行动循环次数

    Returns:
        dict: {"success": bool, "result": str, "iterations": int, "cost": float}
    """
    from ..config.loader import load_config
    config = load_config()
    active_ai = _get_active_ai_config(config)

    # 选择模型
    actual_model = model_name or active_ai.get("model", "deepseek-chat")
    model = get_model(actual_model)

    # 上下文管理器
    ctx = ContextManager(task=task, session_id=session_id)

    # 系统 prompt
    system_prompt = _build_system_prompt(config)

    # 初始化消息
    messages = [{"role": "system", "content": system_prompt}]

    # 加载历史对话（带截断保护）
    if session_id:
        try:
            from ..agent.conversation import get_session_messages
            history = get_session_messages(session_id, limit=30)
            # 估算 token：跳过太长的历史，从后往前保留最多 ~16K tokens 的上下文
            hist_tokens = 0
            kept = []
            for m in reversed(history):
                t = len(m.get("content", "")) // 2
                if hist_tokens + t > 16000:
                    break
                kept.insert(0, {"role": m["role"], "content": m["content"]})
                hist_tokens += t
            messages.extend(kept)
            if len(kept) < len(history):
                logger.info(f"📜 加载 {len(history)} 条历史，保留最近 {len(kept)} 条 (约 {hist_tokens} tokens)")
            else:
                logger.info(f"📜 加载 {len(kept)} 条历史对话上下文")
        except Exception as e:
            logger.warning(f"加载历史失败: {e}")

    messages.append({"role": "user", "content": task})

    total_cost = 0.0
    final_result = ""
    all_logs = []

    for iteration in range(1, max_iterations + 1):
        logger.info(f"🔄 Agent 迭代 {iteration}/{max_iterations}")

        try:
            response = _call_llm(
                model=model,
                messages=messages,
                tools=get_all_tools(),
                config=config,
            )
        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}")
            ctx.add_assistant_message(f"❌ LLM 调用失败: {e}")
            return {
                "success": False,
                "result": f"LLM 调用失败: {e}",
                "iterations": iteration,
                "cost": total_cost,
                "logs": all_logs,
            }

        # 记录费用
        usage = response.usage
        if usage:
            cost = track_cost_internal(
                model=actual_model,
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
            )
            total_cost += cost

        choice = response.choices[0]
        msg = choice.message
        finish_reason = choice.finish_reason or ""

        # 添加 assistant 消息到历史
        # 将 pydantic model 转为 dict 以保持兼容
        msg_dict = msg.model_dump(exclude_none=True)
        messages.append(msg_dict)

        # 记录到对话历史
        content = msg.content or ""
        tool_calls_raw = msg.tool_calls
        log_entry = {
            "iteration": iteration,
            "role": "assistant",
            "content": content,
            "tool_calls": [tc.model_dump() for tc in tool_calls_raw] if tool_calls_raw else None,
            "finish_reason": finish_reason,
        }
        all_logs.append(log_entry)

        # 保存对话到数据库
        if content:
            ctx.add_assistant_message(content)

        # 如果有文本回复，记录
        if content:
            logger.info(f"💬 Agent: {content[:100]}...")

        # 判断是否需要工具调用
        if finish_reason == "stop" or (not tool_calls_raw and content):
            final_result = content or "任务完成"
            return {
                "success": True,
                "result": final_result,
                "iterations": iteration,
                "cost": total_cost,
                "logs": all_logs,
            }

        # 处理工具调用
        if not tool_calls_raw:
            # 没有工具调用也没有文本 — 让模型继续
            messages.append({"role": "user", "content": "请继续完成任务，或调用工具。"})
            continue

        for tc in tool_calls_raw:
            func = tc.function
            tool_name = func.name
            tool_args = json.loads(func.arguments)

            tool_def = get_tool(tool_name)
            danger_label = "⚠️" if (tool_def and tool_def.dangerous) else ""
            logger.info(f"🔧 {danger_label}调用工具: {tool_name}({_truncate_args(tool_args)})")

            # 执行工具
            result_str = execute_tool(tool_name, tool_args)

            # 截断过长结果
            if len(result_str) > 8000:
                result_str = result_str[:8000] + "\n...(结果已截断)"

            logger.debug(f"   结果: {result_str[:100]}...")

            # 添加到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

    # 达到最大迭代次数
    logger.warning(f"⚠️ 达到最大迭代次数 {max_iterations}")
    return {
        "success": False,
        "result": f"达到最大迭代次数 {max_iterations}，任务未完成",
        "iterations": max_iterations,
        "cost": total_cost,
        "logs": all_logs,
    }


def _call_llm(model, messages: list, tools: list, config: dict) -> dict:
    """调用 LLM API"""
    active_cfg = _get_active_ai_config(config)
    provider = active_cfg.get("provider", "deepseek")
    temperature = active_cfg.get("temperature", 0.7)
    max_tokens = active_cfg.get("max_tokens", 4096)

    kwargs = {
        "model": model.get_api_name(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    # 记录请求日志
    req_start = time.time()
    response = model.chat(**kwargs)
    elapsed = time.time() - req_start
    logger.debug(f"⏱️ API 响应: {elapsed:.2f}s")

    return response


def _build_system_prompt(config: dict) -> str:
    """构建系统提示词"""
    ai_cfg = config.get("ai", {})
    default_prompt = ai_cfg.get("system_prompt", "")

    # 如果有自定义 prompt 文件，优先使用
    from pathlib import Path
    custom_prompt = Path("data/prompts/system.txt")
    if custom_prompt.exists():
        return custom_prompt.read_text(encoding="utf-8")

    if default_prompt:
        return default_prompt

    # 默认 prompt
    return """你是一个智能 AI 编辑，负责自动抓取、改写和发布游戏/软件资源到7坛网站。

你的能力：
1. 浏览网页发现新资源
2. 下载文件并验证
3. AI 改写简介和描述
4. 上传截图/文件到云存储
5. 自动发布到7坛管理后台

规则：
- 下载前先检查磁盘空间
- 发布前必须检查敏感词
- 所有操作记录到数据库
- 遇到错误时自我修正
- 完成后汇报结果

请根据用户指令，逐步完成任务。每步只调用一个工具。"""


def track_cost_internal(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """内部费用追踪（返回费用值）"""
    from ..tools.monitor_tools import _estimate_cost
    cost = _estimate_cost(model, prompt_tokens, completion_tokens)
    track_cost(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=cost,
    )
    return cost


def _truncate_args(args: dict) -> str:
    """截断工具参数显示"""
    s = json.dumps(args, ensure_ascii=False)
    if len(s) > 80:
        return s[:77] + "..."
    return s
