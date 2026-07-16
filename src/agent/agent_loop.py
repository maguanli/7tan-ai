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
MAX_ITERATIONS = 80  # 浏览列表多页任务需要更多步数


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
                # 保留所有字段（tool_calls, tool_call_id 等），加载对应 tool 回复
                entry = {"role": m["role"], "content": m.get("content", "")}
                if "tool_calls" in m and m["tool_calls"]:
                    entry["tool_calls"] = m["tool_calls"]
                if "tool_call_id" in m and m["tool_call_id"]:
                    entry["tool_call_id"] = m["tool_call_id"]
                kept.insert(0, entry)
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
    last_calls = []  # 防重复循环检测

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
        # DeepSeek 严格校验: 空 tool_calls 数组也触发配对检查, 必须剔除
        if "tool_calls" in msg_dict and (not msg_dict["tool_calls"]):
            del msg_dict["tool_calls"]
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
        # "length" = 输出被截断，不能当完成！
        if finish_reason == "length":
            # 输出被截断，提示继续
            messages.append({"role": "user", "content": "你的输出被截断了，请从中断处继续生成剩余内容，不要重复已输出的部分。"})
            continue
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
            # 兼容 openai 库新版返回 dict 而不是对象
            func = tc.function if hasattr(tc, 'function') else tc.get("function", {})
            tool_name = func.name if hasattr(func, 'name') else func.get("name", "unknown")
            tool_args_raw = func.arguments if hasattr(func, 'arguments') else func.get("arguments", "{}")
            tool_id = tc.id if hasattr(tc, 'id') else tc.get("id", "")
            tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw

            tool_def = get_tool(tool_name)
            danger_label = "⚠️" if (tool_def and tool_def.dangerous) else ""
            logger.info(f"🔧 {danger_label}调用工具: {tool_name}({_truncate_args(tool_args)})")

            # 检测重复调用死循环
            call_sig = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
            last_calls.append(call_sig)
            if len(last_calls) > 5:
                last_calls.pop(0)
            if len(last_calls) >= 3 and len(set(last_calls[-3:])) == 1:
                logger.warning(f"⚠️ 检测到重复调用死循环: {call_sig}")
                return {
                    "success": False,
                    "result": f"⚠️ 检测到死循环 — 工具 {tool_name} 连续调用 3 次相同参数，已自动停止。\n请尝试不同的方法或简化任务。",
                    "iterations": iteration,
                    "cost": total_cost,
                    "logs": all_logs,
                }

            # 执行工具
            result_str = execute_tool(tool_name, tool_args)

            # 截断过长结果（硬保护，极高上限）
            if len(result_str) > 100000:
                result_str = result_str[:100000] + "\n...(结果已截断)"

            logger.debug(f"   结果: {result_str[:100]}...")

            # 添加到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
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
    return """你是一个专业的游戏资源编辑 AI，负责从游戏网站发现、整理并发布游戏资源到7坛平台。

【核心任务流程】
1. 浏览游戏网站，发现新游戏
2. 提取游戏的完整信息（名称、简介、LOGO、截图、下载地址）
3. 将文件下载到本地，必要时上传到OSS云存储
4. 整理好所有信息后，调用 publish_to_7tan 一键发布

【发布前必须收集的内容】
- title: 游戏名称（必须）
- intro: 游戏简介（必须，至少100字，包含玩法、特色、截图描述等）
- download_url: 下载链接（必须，优先使用 OSS 上传后的外链）
- logo_path: 游戏 LOGO 本地路径（强烈建议，下载页面上的 LOGO 图片）
- screenshot_paths: 游戏截图本地路径（强烈建议，下载2-4张截图，JSON数组格式如 '["path1","path2"]'）
- category: 分类名称
- tags: 标签（逗号分隔）

【如何找到下载链接】
1. 先用 browse_page 浏览游戏详情页
2. 用 find_download_links 查找页面中的下载地址
3. 如果 find_download_links 没找到，用 click_element 点击页面上的"下载"按钮触发真实下载链接
4. 下载链接通常包含 .apk/.ipa/.zip/.rar 等扩展名，或者含 download/down/apk 关键词

【如何写简介】
- 不要只写游戏名称！必须包含：游戏类型、核心玩法、画面风格、特色功能
- 参考页面上的官方描述，但需要用 AI 改写润色
- 字数至少 100 字，越详细越好
- 格式使用 HTML（<p>、<br>、<b>等标签）

【下载和上传】
- 用 download_file 下载文件到 downloads/packages/
- 如果需要在简介中插入图片，用 oss_upload 上传到 OSS 获得外链
- LOGO 和截图先用 download_file 下载到本地，再传给 publish_to_7tan

【重要规则】
- 每步只调用一个工具，逐步完成任务
- 发布前必须用 check_content_quality 检查内容质量
- 发布前必须用 check_sensitive_words 检查敏感词
- 下载前先检查磁盘空间
- 遇到错误时尝试修复并重试
- 完成后汇报发布结果"""



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
