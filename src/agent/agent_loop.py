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

# 🔒 重型工具互斥集合——防止并发执行构建/测试等重型操作
_HEAVY_TOOLS = {
    "run_build", "run_tests", "run_coverage", "install_deps",
    "run_command", "run_shell_script", "self_rebuild", "sandbox_execute",
}
import threading
_heavy_lock = threading.Lock()
from .agent_optimizer import (
    execute_tools_parallel,
    get_file_replace_hint,
    find_affected_tests,
    build_incremental_test_cmd,
    get_workspace_status,
    filter_history_by_mode,
    should_compress_context,
    compress_context,
    get_optimized_system_prompt_addition,
)

# 最大迭代次数（防止无限循环）
MAX_ITERATIONS = 300  # 浏览列表多页任务需要更多步数

def _get_timeout_from_config() -> int:
    """从配置读取超时时间（秒），默认 600"""
    try:
        from ..config.loader import load_config
        config = load_config()
        return config.get("agent", {}).get("loop_timeout", 600)
    except Exception:
        return 600

# Agent 循环超时（从配置读取）
AGENT_LOOP_TIMEOUT = _get_timeout_from_config()


# ============================================================
# 🚀 Token 效率优化模块（任务模式识别 / 工具筛选 / 结果截断 / 文件缓存）
# ============================================================

def _detect_task_mode(task: str) -> str:
    """根据任务描述识别场景，用于裁剪 system prompt 和筛选工具

    Returns:
        'code'         — 代码编写/调试/重构/测试/Git 等开发任务
        'game_publish' — 游戏资源浏览/下载/发布任务
        'general'      — 其他/无法判断（保守全量）
    """
    t = task.lower()
    # 游戏发布场景特征词（优先匹配，因为特征强）
    game_kw = [
        "发布到", "一键发布", "publish_to_7tan", "游戏详情页", "下载链接",
        "find_download_links", "browse_page", "游戏简介", "截图", "logo",
        "oss_upload", "db_save_resource", "采集", "游戏资源", "新游戏",
        "游戏站", "详情页", "get_page_images",
    ]
    if any(k in t for k in game_kw):
        return "game_publish"
    # 代码开发场景特征词
    code_kw = [
        "代码", "bug", "修复", "重构", "函数", "类", "报错", "错误",
        "refactor", "debug", "fix", "implement", "写一个", "优化",
        "python", "def ", "class ", "git", "commit", "分支", "测试",
        "test", "运行测试", "单元测试", "覆盖率", "依赖", "import",
        "语法", "编译", "构建", "build", "打包", "插件", "脚本",
        "审查", "review", "格式化", "重命名", "查找引用", "跳转定义",
        ".py", ".js", ".ts", "接口", "api", "性能", "profile",
    ]
    if any(k in t for k in code_kw):
        return "code"
    return "general"


# 场景工具白名单 — None 表示不筛选（全量）
_CODE_TOOLS = {
    # 代码搜索与结构
    "grep_code", "find_files", "search_in_files", "find_references",
    "list_functions", "analyze_imports", "scan_project", "code_stats",
    "list_templates", "create_project",
    # LSP
    "go_to_definition", "find_all_references", "get_diagnostics",
    "get_completions", "get_hover_info",
    # 文件读写
    "read_file_content", "write_file", "list_files", "file_replace",
    "delete_file", "compress_image",
    # Git
    "git_status", "git_diff", "git_log", "git_add", "git_commit",
    "git_push", "git_pull", "git_branch", "git_checkout", "git_clone",
    "git_init", "git_stash", "git_tag", "git_remote_info",
    "git_check_commit_message", "git_init_hooks", "git_contributors",
    "check_changes", "compare_branches", "resolve_conflict", "generate_diff",
    # 测试
    "run_tests", "run_coverage", "discover_tests", "generate_test_template",
    # 终端与构建
    "run_command", "run_build", "install_deps", "check_env",
    "run_shell_script", "system_shell", "gradle_build", "deploy_pipeline",
    # 重构与文档
    "rename_symbol", "organize_imports", "format_code", "extract_function",
    "generate_docstring", "generate_readme", "analyze_api_routes",
    "generate_gitignore", "generate_ci_config", "generate_changelog", "bump_version",
    # 代码审查与依赖
    "code_review_file", "code_review_directory", "security_scan_file",
    "check_dependencies", "detect_circular_imports", "generate_dependency_graph",
    "check_outdated", "scan_secrets", "generate_env_template", "manage_env",
    # 调试诊断
    "analyze_error", "analyze_log", "diagnose_crash",
    # 性能
    "benchmark_function", "profile_code_block", "check_memory",
    # 数据库探索 / API
    "explore_db", "query_db", "generate_model",
    "http_request", "test_api_endpoint", "openapi_explore",
    # 片段 / 补全
    "save_snippet", "search_snippets", "get_snippet", "list_snippets",
    "completion_start", "completion_stop", "completion_status",
    # VS Code
    "vscode_open_file", "vscode_open_project", "vscode_open_multi",
    "vscode_diff", "vscode_list_extensions", "vscode_install_extension",
    # 自我管理 / 沙盒
    "sandbox_execute", "self_modify_config", "self_update_prompt",
    "self_fix_sandbox", "check_file_integrity", "verify_integrity",
    "self_diagnose", "create_plugin", "memory_store", "memory_recall",
    "memory_summary", "memory_forget",
    # 监控 / 通用自我管理
    "track_cost", "get_cost_report", "health_check", "get_system_status",
    "check_disk", "web_search", "fetch_news",
    "self_rebuild", "self_restart", "verify_integrity",
    # 内容质量（通用）
    "check_sensitive_words", "check_content_quality",
}

_GAME_PUBLISH_TOOLS = {
    # 浏览器
    "use_source_browser", "use_admin_browser", "browse_page", "scroll_down",
    "click_element", "screenshot", "get_page_images", "find_download_links",
    "extract_logo", "auto_screenshot", "ocr_screenshot", "login_7tan",
    # 文件 / 下载 / 图片
    "download_file", "check_disk", "read_file_content", "write_file",
    "list_files", "delete_file", "compress_image",
    # OSS / 发布
    "oss_upload", "oss_delete", "publish_to_7tan",
    "detect_form_fields", "fill_all_fields",
    # 数据库
    "db_check_duplicate", "db_save_resource", "db_query_resources",
    "db_check_version", "db_add_task_log",
    # 内容处理 / AI
    "analyze_game", "compare_games", "summarize_reviews", "cloud_write_intro",
    "cloud_analyze", "translate_text", "check_sensitive_words",
    "check_content_quality", "web_search", "fetch_news",
    # 监控 / 通用自我管理
    "track_cost", "get_cost_report", "health_check", "get_system_status",
    "sandbox_execute", "self_modify_config", "self_rebuild", "self_restart",
    "self_update_prompt", "verify_integrity",
    "memory_store", "memory_recall",
}


def get_tools_for_mode(mode: str) -> list:
    """按任务模式返回筛选后的工具定义列表（OpenAI tools 格式）

    general / 未知模式 → 全量（保守，保证功能不缺失）
    """
    all_tools = get_all_tools()
    if mode == "code":
        allowed = _CODE_TOOLS
    elif mode == "game_publish":
        allowed = _GAME_PUBLISH_TOOLS
    else:
        return all_tools
    filtered = [t for t in all_tools if t["function"]["name"] in allowed]
    logger.info(
        f"🎯 工具筛选[{mode}]: {len(all_tools)} → {len(filtered)} "
        f"(省 ~{(len(all_tools)-len(filtered))*80} tokens)"
    )
    return filtered


# 工具结果软截断阈值（字符）。超过则按类型智能摘要，避免消息历史膨胀。
_SOFT_TRUNCATE_LIMIT = 2500

# 按工具定制的截断策略：保留关键信息，丢弃冗余项
_KEEP_HEAD_TOOLS = {           # 只保留前 N 字符 + 统计
    "scan_project", "code_review_directory", "analyze_imports",
    "generate_dependency_graph", "discover_tests", "browse_page",
}


def _smart_truncate_tool_result(tool_name: str, result: str) -> str:
    """对工具结果做智能截断，防止消息历史膨胀（在 100K 硬截断之前生效）

    策略：
      - 短结果原样返回
      - 特定工具保留头部 + 附加统计
      - 其余超长结果保留头尾，省略中段
    """
    if not isinstance(result, str):
        result = str(result)
    n = len(result)
    if n <= _SOFT_TRUNCATE_LIMIT:
        return result
    # 保留头部型
    if tool_name in _KEEP_HEAD_TOOLS:
        head = result[:_SOFT_TRUNCATE_LIMIT]
        return f"{head}\n\n…[已截断：共 {n} 字符，仅显示前 {_SOFT_TRUNCATE_LIMIT}。需要完整内容请缩小范围后重查]"
    # 头尾保留型（默认）
    head = result[:1800]
    tail = result[-500:]
    omitted = n - 2300
    return (
        f"{head}\n\n…[中间省略 {omitted} 字符]…\n\n{tail}"
        f"\n\n(完整结果 {n} 字符，已智能截断)"
    )


# ---- 请求级文件缓存（生命周期 = 单次 run_agent_loop） ----
_request_file_cache: dict = {}


def _cache_get(path: str):
    """读取缓存；mtime 变化则失效"""
    import os
    entry = _request_file_cache.get(path)
    if not entry:
        return None
    try:
        if os.path.getmtime(path) == entry[1]:
            return entry[0]
    except OSError:
        pass
    _request_file_cache.pop(path, None)
    return None


def _cache_put(path: str, content) -> None:
    import os
    try:
        _request_file_cache[path] = (content, os.path.getmtime(path))
    except OSError:
        _request_file_cache[path] = (content, 0)


def _clear_request_cache() -> None:
    """请求结束清空缓存，避免内存泄漏"""
    _request_file_cache.clear()


def _execute_tool_cached(name: str, args: dict) -> str:
    """🚀 带请求级缓存的工具执行包装

    对只读文件类工具做缓存：同一请求内重复读取同一文件直接命中缓存，
    避免重复磁盘 I/O 与重复结果进入消息历史。
    缓存以文件 mtime 失效，写操作后自动失效，保证一致性。
    """
    _CACHEABLE = {"read_file_content"}
    if name in _CACHEABLE:
        path = args.get("path") or args.get("file_path") or ""
        # 仅当无 offset/max_lines 这类部分读取参数时才整文件缓存
        if path and not args.get("offset") and not args.get("max_lines"):
            hit = _cache_get(path)
            if hit is not None:
                logger.debug(f"📦 文件缓存命中: {path}")
                return hit
            result = execute_tool(name, args)
            _cache_put(path, result)
            return result
    result = execute_tool(name, args)
    # 写操作后使对应文件缓存失效
    if name in ("write_file", "file_replace", "delete_file"):
        path = args.get("path") or args.get("file_path") or args.get("filepath") or ""
        if path:
            _request_file_cache.pop(path, None)
    return result


def _get_active_ai_config(config: dict) -> dict:
    """从数据库获取当前活跃 AI 配置"""
    try:
        from ..database.db import get_active_ai_config_raw
        cfg = get_active_ai_config_raw()
        if cfg:
            return cfg
    except Exception:
        pass
    # 回退：从 config dict 读取（兼容旧格式）
    ai = config.get("ai", {})
    if "configs" in ai:
        active_key = ai.get("active", "deepseek")
        return ai["configs"].get(active_key, {})
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

    # 🚀 识别任务模式（用于工具筛选 + 分层 prompt）
    task_mode = _detect_task_mode(task)
    if task_mode != "general":
        logger.info(f"🧭 任务模式识别: {task_mode}")
    _clear_request_cache()  # 🚀 初始化请求级文件缓存

    # 选择模型
    actual_model = model_name or active_ai.get("model", "")
    model = get_model(actual_model)

    # 上下文管理器
    ctx = ContextManager(task=task, session_id=session_id)

    # 🚀 系统 prompt（按模式分层裁剪 + 模式专属补充）
    system_prompt = _build_system_prompt(config, task_mode)
    system_prompt += get_optimized_system_prompt_addition(task_mode)

    # 🚀 自动注入工作区状态（git status --short）
    workspace_status = get_workspace_status()
    if workspace_status:
        system_prompt += f"\n\n{workspace_status}"

    # 初始化消息
    timeout_note = f"\n\n【时间限制】本轮任务超时时间为 {AGENT_LOOP_TIMEOUT} 秒（约 {AGENT_LOOP_TIMEOUT//60} 分钟）。请合理规划步骤，避免不必要的大文件重复下载。如果时间紧迫，优先完成任务的核心部分。"
    messages = [{"role": "system", "content": system_prompt + timeout_note}]

    # 加载历史对话（带截断保护 + 模式过滤）
    if session_id:
        try:
            from ..agent.conversation import get_session_messages
            history = get_session_messages(session_id, limit=30)
            # 🚀 按任务模式过滤历史对话
            history = filter_history_by_mode(history, task_mode)
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
            # 修复历史中可能存在的孤儿 tool_calls
            if kept:
                messages = _repair_messages(messages)
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
    start_time = time.time()  # 超时感知：记录开始时间
    timeout_warned = False    # 是否已发出超时警告

    for iteration in range(1, max_iterations + 1):
        # 超时感知：检查剩余时间
        elapsed = time.time() - start_time
        remaining = AGENT_LOOP_TIMEOUT - elapsed
        if remaining < 120 and not timeout_warned:
            timeout_warned = True
            logger.warning(f"⏰ 距超时还有 {remaining:.0f} 秒，请尽快完成任务！")
            messages.append({
                "role": "user",
                "content": f"⚠️ 距超时还有约 {remaining:.0f} 秒！请跳过非必需步骤，直接给出当前已完成的结果。"
            })
        elif remaining < 30:
            logger.error(f"⏰ 仅剩 {remaining:.0f} 秒，强制退出循环")
            return {
                "success": False,
                "result": f"⏰ 任务超时（已用 {elapsed:.0f} 秒）。请分步执行或简化任务后重试。",
                "iterations": iteration,
                "cost": total_cost,
                "logs": all_logs,
            }
        logger.info(f"🔄 Agent 迭代 {iteration}/{max_iterations}")

        try:
            # 诊断: 打印每条消息的角色和类型
            for i, m in enumerate(messages):
                role = m.get("role", "?")
                pass  # 消息摘要已静音

            # 🔒 安全检查：修复孤立的 assistant tool_calls（防止 API 400 错误）
            messages = _repair_messages(messages)
            
            response = _call_llm(
                model=model,
                messages=messages,
                tools=get_tools_for_mode(task_mode),
                config=config,
            )
        except Exception as e:
            import traceback
            logger.error(f"❌ LLM 调用失败: {e}\n{traceback.format_exc()}")
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
        msg_dict = {"role": "assistant"}
        if msg.content:
            msg_dict["content"] = msg.content
        if msg.tool_calls:
            # 开放式API格式: 只保留 id/type/function 三个字段
            safe_calls = []
            for tc in msg.tool_calls:
                fn = tc.function
                safe_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": fn.name if hasattr(fn, 'name') else fn.get("name", ""),
                        "arguments": fn.arguments if hasattr(fn, 'arguments') else fn.get("arguments", ""),
                    }
                })
            msg_dict["tool_calls"] = safe_calls
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

        # 🚀 上下文压缩检查（在工具调用前）
        if should_compress_context(ctx._total_tokens):
            logger.info("🗜️ 上下文过大，执行压缩...")
            summary = compress_context(ctx, model=model)
            if summary:
                messages = [{"role": "system", "content": system_prompt + timeout_note}]
                messages.extend(ctx.get_messages())
                logger.info(f"🗜️ 上下文压缩完成，摘要长度: {len(summary)}")

        # 处理工具调用
        if not tool_calls_raw:
            # 没有工具调用也没有文本 — 让模型继续
            messages.append({"role": "user", "content": "请继续完成任务，或调用工具。"})
            continue

        # 🚀 并行执行独立工具（⭐5）
        tc_dicts = []
        for tc in tool_calls_raw:
            func = tc.function if hasattr(tc, 'function') else tc.get("function", {})
            tc_dicts.append({
                "id": tc.id if hasattr(tc, 'id') else tc.get("id", ""),
                "type": "function",
                "function": {
                    "name": func.name if hasattr(func, 'name') else func.get("name", "unknown"),
                    "arguments": func.arguments if hasattr(func, 'arguments') else func.get("arguments", "{}"),
                }
            })

        def _execute_single_tool(name: str, args: dict) -> str:
            acquired = False
            if name in _HEAVY_TOOLS:
                acquired = _heavy_lock.acquire(blocking=False)
                if not acquired:
                    return "⚠️ 另一个重型操作（构建/测试/安装）正在运行中，请等待其完成后再试。"
            try:
                result = _execute_tool_cached(name, args)
                result = _smart_truncate_tool_result(name, result)
                if len(result) > 100000:
                    result = result[:100000] + "\n...(结果已截断)"
                return result
            except Exception as e:
                import traceback
                logger.error(f"❌ 工具执行失败 [{name}]: {e}\n{traceback.format_exc()}")
                return f"❌ 工具执行失败: {e}"
            finally:
                if name in _HEAVY_TOOLS and acquired:
                    _heavy_lock.release()

        tool_results = execute_tools_parallel(tc_dicts, _execute_single_tool)

        assistant_msg = msg_dict
        for tc, result in zip(tool_calls_raw, tool_results):
            try:
                # 兼容 openai 库新版返回 dict 而不是对象
                func = tc.function if hasattr(tc, 'function') else tc.get("function", {})
                tool_name = func.name if hasattr(func, 'name') else func.get("name", "unknown")
                tool_args_raw = func.arguments if hasattr(func, 'arguments') else func.get("arguments", "{}")
                tool_id = tc.id if hasattr(tc, 'id') else tc.get("id", "")
                tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw

                logger.info(f"🔧 调用工具: {tool_name}({_truncate_args(tool_args)})")

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

                result_str = result["content"]

            except Exception as tool_err:
                import traceback
                logger.error(f"❌ 工具执行失败 [{tool_name}]: {tool_err}\n{traceback.format_exc()}")
                result_str = f"❌ 工具执行失败: {tool_err}"

            # 无论如何都要添加到消息历史（防止孤立的 assistant tool_calls）
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


def _repair_messages(messages: list) -> list:
    """修复消息历史中的孤儿 tool_calls，防止 API 400 错误
    
    API 要求：assistant 消息的 tool_calls 必须紧跟着对应的 tool 响应消息。
    如果发现缺失，在正确位置补上占位消息。
    """
    repaired = []
    pending_calls = {}     # tool_call_id → tool_name
    pending_insert_at = 0  # 已修复的 tool 消息应该插入的位置
    
    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        
        if role == "assistant" and msg.get("tool_calls"):
            # 先把上一轮未处理的孤儿 tool_calls 补上
            if pending_calls:
                for missing_id, tool_name in pending_calls.items():
                    logger.warning(f"🔧 修复孤立 tool_call: id={missing_id}, tool={tool_name}")
                    repaired.insert(pending_insert_at, {
                        "role": "tool",
                        "tool_call_id": missing_id,
                        "content": f"⚠️ 工具 {tool_name} 的响应丢失，请重试此操作。",
                    })
                    pending_insert_at += 1
                pending_calls.clear()
            
            # 重新设置 pending 列表（先清理上一轮可能残留的）
            pending_calls.clear()
            for tc in msg["tool_calls"]:
                pending_calls[tc["id"]] = tc.get("function", {}).get("name", "unknown")
            
            repaired.append(msg)
            pending_insert_at = len(repaired)  # tool 响应应该从这里开始插入
            
        elif role == "tool":
            tid = msg.get("tool_call_id", "")
            if tid in pending_calls:
                del pending_calls[tid]
            repaired.append(msg)
        else:
            # 遇到非 tool 消息，先把未处理的孤儿 tool_calls 补上
            if pending_calls:
                for missing_id, tool_name in pending_calls.items():
                    logger.warning(f"🔧 修复孤立 tool_call: id={missing_id}, tool={tool_name}")
                    repaired.insert(pending_insert_at, {
                        "role": "tool",
                        "tool_call_id": missing_id,
                        "content": f"⚠️ 工具 {tool_name} 的响应丢失，请重试此操作。",
                    })
                    pending_insert_at += 1
                pending_calls.clear()
            repaired.append(msg)
    
    # 末尾还有未处理的孤儿 tool_calls
    if pending_calls:
        for missing_id, tool_name in pending_calls.items():
            logger.warning(f"🔧 修复孤立 tool_call: id={missing_id}, tool={tool_name}")
            repaired.insert(pending_insert_at, {
                "role": "tool",
                "tool_call_id": missing_id,
                "content": f"⚠️ 工具 {tool_name} 的响应丢失，请重试此操作。",
            })
            pending_insert_at += 1
        pending_calls.clear()
    
    return repaired


def _call_llm(model, messages: list, tools: list, config: dict) -> dict:
    """调用 LLM API"""
    active_cfg = _get_active_ai_config(config)
    provider = active_cfg.get("provider", "deepseek")
    temperature = active_cfg.get("temperature", 0.7)
    max_tokens = active_cfg.get("max_tokens", 4096)

    kwargs = {
        "model": model.get_api_name(),
        "messages": messages,
        "max_tokens": max_tokens,
    }

    # Kimi K3 (moonshot) 只接受 temperature=1，DeepSeek 不需要显式传入
    # 对这两个 provider 不设 temperature，让 API 用默认值
    if provider not in ("moonshot", "deepseek"):
        kwargs["temperature"] = temperature

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    # 记录请求日志
    req_start = time.time()
    response = model.chat(**kwargs)
    elapsed = time.time() - req_start
    logger.debug(f"⏱️ API 响应: {elapsed:.2f}s")

    return response


def _trim_prompt_for_mode(prompt: str, task_mode: str) -> str:
    """🚀 按任务模式裁剪 system prompt 中与场景无关的模块（分层 prompt）

    设计原则：
      - 始终保留：核心身份 / 安全边界 / 重启构建硬性规则 / 铁律 / 自由原则
      - code 模式：裁掉游戏专业知识、简介撰写规范、浏览网页规则、发布流程、能力清单大表
      - game_publish 模式：保留全部（本来就是为它写的）
      - general 模式：保留全部
    通过 Markdown 二级标题(## )切分模块，仅移除命中的整块，保证结构完整。
    """
    if task_mode not in ("code",):
        return prompt  # game_publish / general 不裁剪

    # code 模式下要移除的模块关键词（兼容 ## / ### / 无标题情况）
    drop_keywords = [
        "游戏领域专业知识",
        "游戏简介撰写规范",
        "浏览网页规则",
        "发布流程",
        "能力清单速览",
        "能力清单索引",
    ]
    lines = prompt.splitlines()
    out = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        # 任何级别的 Markdown 标题都视为新 section 开始
        if stripped.startswith("#"):
            skipping = any(k in stripped for k in drop_keywords)
            continue
        # 无标题但命中关键词的段落也跳过（防御数据库 prompt 无标题）
        if not skipping and any(k in stripped for k in drop_keywords):
            skipping = True
            continue
        if not skipping:
            out.append(line)
    trimmed = "\n".join(out)
    saved = len(prompt) - len(trimmed)
    if saved > 0:
        logger.info(f"✂️ 分层 Prompt[{task_mode}]: {len(prompt)} → {len(trimmed)} 字符 (省 ~{saved//2} tokens)")
    return trimmed


def _build_system_prompt(config: dict, task_mode: str = "general") -> str:
    """构建系统提示词 — 数据库优先，文件回退；按 task_mode 分层裁剪"""
    full = None
    # 1. 优先从数据库读取（通过 prompts 模块）
    try:
        from .prompts import get_prompt
        db_prompt = get_prompt("system")
        if db_prompt and db_prompt.strip() and len(db_prompt) > 200:
            full = db_prompt
    except Exception:
        pass

    # 2. 回退到文件
    if full is None:
        from pathlib import Path
        custom_prompt = Path("data/prompts/system.txt")
        if custom_prompt.exists():
            content = custom_prompt.read_text(encoding="utf-8")
            if content.strip():
                full = content

    # 3. 回退到配置文件
    if full is None:
        ai_cfg = config.get("ai", {})
        default_prompt = ai_cfg.get("system_prompt", "")
        if default_prompt:
            full = default_prompt

    if full is not None:
        return _trim_prompt_for_mode(full, task_mode)

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



def run_agent_loop_streaming(
    task: str,
    session_id: str = None,
    model_name: str = None,
    max_iterations: int = 300,
):
    """
    流式 Agent 循环 — 逐步 yield 事件给前端展示思考过程

    Yields:
        dict: 事件类型
            {"type": "thinking", "message": "..."}
            {"type": "text_chunk", "content": "..."}
            {"type": "tool_call", "tool_name": "...", "args": {...}}
            {"type": "tool_result", "tool_name": "...", "summary": "...", "error": bool}
            {"type": "iteration", "iteration": 1, "max_iterations": 80}
            {"type": "cost", "cost": 0.001}
            {"type": "done", "success": bool, "result": "...", "cost": 0.0, "iterations": 0}
            {"type": "error", "message": "..."}
    """
    from ..config.loader import load_config
    config = load_config()
    active_ai = _get_active_ai_config(config)

    # 🚀 识别任务模式 + 初始化请求级文件缓存
    task_mode = _detect_task_mode(task)
    if task_mode != "general":
        logger.info(f"🧭 任务模式识别: {task_mode}")
    _clear_request_cache()

    actual_model = model_name or active_ai.get("model", "")
    model = get_model(actual_model)
    ctx = ContextManager(task=task, session_id=session_id)
    system_prompt = _build_system_prompt(config, task_mode)

    messages = [{"role": "system", "content": system_prompt}]

    # 加载历史对话
    if session_id:
        try:
            from ..agent.conversation import get_session_messages
            history = get_session_messages(session_id, limit=30)
            hist_tokens = 0
            kept = []
            for m in reversed(history):
                t = len(m.get("content", "")) // 2
                if hist_tokens + t > 16000:
                    break
                entry = {"role": m["role"], "content": m.get("content", "")}
                if "tool_calls" in m and m["tool_calls"]:
                    entry["tool_calls"] = m["tool_calls"]
                if "tool_call_id" in m and m["tool_call_id"]:
                    entry["tool_call_id"] = m["tool_call_id"]
                kept.insert(0, entry)
                hist_tokens += t
            messages.extend(kept)
            if kept:
                messages = _repair_messages(messages)
        except Exception as e:
            logger.warning(f"\u52a0\u8f7d\u5386\u53f2\u5931\u8d25: {e}")

    messages.append({"role": "user", "content": task})
    yield {"type": "thinking", "message": "\uf0e7\u5df2\u52a0\u8f7d\u4efb\u52a1\uff0c\u5f00\u59cb\u5904\u7406..."}

    total_cost = 0.0
    all_logs = []
    last_calls = []

    for iteration in range(1, max_iterations + 1):
        yield {"type": "iteration", "iteration": iteration, "max_iterations": max_iterations}
        yield {"type": "thinking", "message": f"\uf0e7\u7b2c {iteration}/{max_iterations} \u8f6e\u63a8\u7406..."}

        try:
            messages = _repair_messages(messages)
            response = _call_llm(
                model=model,
                messages=messages,
                tools=get_tools_for_mode(task_mode),
                config=config,
            )
        except Exception as e:
            import traceback
            logger.error(f"\u274c LLM \u8c03\u7528\u5931\u8d25: {e}\n{traceback.format_exc()}")
            ctx.add_assistant_message(f"\u274c LLM \u8c03\u7528\u5931\u8d25: {e}")
            yield {"type": "error", "message": f"LLM \u8c03\u7528\u5931\u8d25: {e}"}
            yield {"type": "done", "success": False, "result": f"LLM \u8c03\u7528\u5931\u8d25: {e}", "cost": total_cost, "iterations": iteration}
            return

        usage = response.usage
        if usage:
            cost = track_cost_internal(
                model=actual_model,
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
            )
            total_cost += cost
            yield {"type": "cost", "cost": cost}

        choice = response.choices[0]
        msg = choice.message
        finish_reason = choice.finish_reason or ""

        msg_dict = {"role": "assistant"}
        if msg.content:
            msg_dict["content"] = msg.content
        if msg.tool_calls:
            safe_calls = []
            for tc in msg.tool_calls:
                fn = tc.function
                safe_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": fn.name if hasattr(fn, 'name') else fn.get("name", ""),
                        "arguments": fn.arguments if hasattr(fn, 'arguments') else fn.get("arguments", ""),
                    }
                })
            msg_dict["tool_calls"] = safe_calls
        messages.append(msg_dict)

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

        if content:
            ctx.add_assistant_message(content)
            yield {"type": "text_chunk", "content": content}

        if finish_reason == "length":
            messages.append({"role": "user", "content": "\u4f60\u7684\u8f93\u51fa\u88ab\u622a\u65ad\u4e86\uff0c\u8bf7\u4ece\u4e2d\u65ad\u5904\u7ee7\u7eed\u751f\u6210\u5269\u4f59\u5185\u5bb9\uff0c\u4e0d\u8981\u91cd\u590d\u5df2\u8f93\u51fa\u7684\u90e8\u5206\u3002"})
            continue
        if finish_reason == "stop" or (not tool_calls_raw and content):
            yield {"type": "thinking", "message": "\u2705 \u4efb\u52a1\u5b8c\u6210"}
            yield {"type": "done", "success": True, "result": content or "\u4efb\u52a1\u5b8c\u6210", "cost": total_cost, "iterations": iteration}
            return

        if not tool_calls_raw:
            messages.append({"role": "user", "content": "\u8bf7\u7ee7\u7eed\u5b8c\u6210\u4efb\u52a1\uff0c\u6216\u8c03\u7528\u5de5\u5177\u3002"})
            continue

        assistant_msg = msg_dict  # 保存引用，供重型工具锁分支使用
        for tc in tool_calls_raw:
            try:
                func = tc.function if hasattr(tc, 'function') else tc.get("function", {})
                tool_name = func.name if hasattr(func, 'name') else func.get("name", "unknown")
                tool_args_raw = func.arguments if hasattr(func, 'arguments') else func.get("arguments", "{}")
                tool_id = tc.id if hasattr(tc, 'id') else tc.get("id", "")
                tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw

                tool_def = get_tool(tool_name)
                logger.info(f"\uf0e7 \u8c03\u7528\u5de5\u5177: {tool_name}({_truncate_args(tool_args)})")

                yield {"type": "tool_call", "tool_name": tool_name, "args": tool_args}

                call_sig = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                last_calls.append(call_sig)
                if len(last_calls) > 5:
                    last_calls.pop(0)
                if len(last_calls) >= 3 and len(set(last_calls[-3:])) == 1:
                    logger.warning(f"\u26a0\ufe0f \u68c0\u6d4b\u5230\u91cd\u590d\u8c03\u7528\u6b7b\u5faa\u73af: {call_sig}")
                    yield {"type": "tool_result", "tool_name": tool_name, "summary": "\u26a0\ufe0f \u68c0\u6d4b\u5230\u6b7b\u5faa\u73af", "error": True}
                    yield {"type": "done", "success": False,
                           "result": f"\u26a0\ufe0f \u68c0\u6d4b\u5230\u6b7b\u5faa\u73af \u2014 \u5de5\u5177 {tool_name} \u8fde\u7eed\u8c03\u7528 3 \u6b21\u76f8\u540c\u53c2\u6570\uff0c\u5df2\u81ea\u52a8\u505c\u6b62\u3002",
                           "cost": total_cost, "iterations": iteration}
                    return

                result_str = _execute_tool_cached(tool_name, tool_args)
                # 🚀 智能截断（软保护）
                result_str = _smart_truncate_tool_result(tool_name, result_str)
                if len(result_str) > 100000:
                    result_str = result_str[:100000] + "\n...(\u7ed3\u679c\u5df2\u622a\u65ad)"

                summary = result_str[:200] + "..." if len(result_str) > 200 else result_str
                yield {"type": "tool_result", "tool_name": tool_name, "summary": summary, "error": False}

            except Exception as tool_err:
                import traceback
                logger.error(f"\u274c \u5de5\u5177\u6267\u884c\u5931\u8d25 [{tool_name}]: {tool_err}\n{traceback.format_exc()}")
                result_str = f"\u274c \u5de5\u5177\u6267\u884c\u5931\u8d25: {tool_err}"
                yield {"type": "tool_result", "tool_name": tool_name, "summary": f"\u274c {tool_err}", "error": True}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result_str,
            })

    yield {"type": "thinking", "message": f"\u26a0\ufe0f \u8fbe\u5230\u6700\u5927\u8fed\u4ee3\u6b21\u6570 {max_iterations}"}
    yield {"type": "done", "success": False,
           "result": f"\u8fbe\u5230\u6700\u5927\u8fed\u4ee3\u6b21\u6570 {max_iterations}\uff0c\u4efb\u52a1\u672a\u5b8c\u6210",
           "cost": total_cost, "iterations": max_iterations}
