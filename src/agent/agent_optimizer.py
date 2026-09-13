"""
Agent 高级优化模块 — 并行执行 / file_replace引导 / 增量测试 / 工作区注入 / 历史过滤 / 上下文压缩
"""
import concurrent.futures
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger


# ============================================================
# ⭐5 独立工具并行执行
# ============================================================

# 工具依赖关系映射：key 依赖 value 中的工具先执行
_TOOL_DEPENDENCIES: dict[str, set[str]] = {
    # 测试相关：先写文件再测试
    "run_tests": {"write_file", "file_replace", "organize_imports", "format_code"},
    "run_coverage": {"write_file", "file_replace"},
    # Git 相关：先写文件再 add/commit
    "git_add": {"write_file", "file_replace"},
    "git_commit": {"git_add", "write_file", "file_replace"},
    "git_push": {"git_commit"},
    # 重构相关：先读取再重构
    "rename_symbol": {"read_file_content", "grep_code", "find_references"},
    "extract_function": {"read_file_content", "list_functions"},
    # 诊断相关：先读取再诊断
    "get_diagnostics": {"read_file_content", "write_file"},
    "code_review_file": {"read_file_content", "write_file"},
    # 构建相关：先写文件再构建
    "run_build": {"write_file", "file_replace"},
    "gradle_build": {"write_file", "file_replace"},
    # 部署相关：先构建再部署
    "deploy_pipeline": {"run_build", "write_file"},
}

# 只读工具（无副作用，可安全并行）
_READONLY_TOOLS = {
    "read_file_content", "list_files", "find_files", "grep_code", "search_in_files",
    "list_functions", "analyze_imports", "scan_project", "code_stats",
    "go_to_definition", "find_all_references", "find_references",
    "get_diagnostics", "get_completions", "get_hover_info",
    "git_status", "git_diff", "git_log", "git_branch", "git_remote_info",
    "git_contributors", "check_changes", "compare_branches",
    "code_review_file", "code_review_directory", "security_scan_file",
    "analyze_error", "analyze_log", "diagnose_crash",
    "benchmark_function", "profile_code_block", "check_memory",
    "explore_db", "query_db", "generate_model",
    "http_request", "test_api_endpoint", "openapi_explore",
    "check_env", "check_disk", "check_outdated", "check_dependencies",
    "detect_circular_imports", "generate_dependency_graph",
    "scan_secrets", "generate_env_template", "manage_env",
    "save_snippet", "search_snippets", "get_snippet", "list_snippets",
    "memory_store", "memory_recall", "memory_summary", "memory_forget",
    "track_cost", "get_cost_report", "health_check", "get_system_status",
    "check_sensitive_words", "check_content_quality",
    "web_search", "fetch_news",
}


# ⭐ 建议A：冷启动敏感工具（首次 import 大库，GIL 竞争下并行反而更慢）
_COLD_START_SENSITIVE_TOOLS = {
    "list_functions", "analyze_imports", "go_to_definition",
    "find_all_references", "get_completions", "get_hover_info",
    "get_diagnostics",  # jedi / AST 系
}


def _should_parallel(independent: list) -> bool:
    """
    判断独立工具集是否值得并行。
    实测结论：
    - 单工具 <0.1s 的快工具并行纯亏线程池开销
    - 冷启动重库（jedi）并行因 GIL 竞争严重变慢
    - 只有含慢工具(I/O/子进程/>0.5s)时并行才有真收益
    """
    if len(independent) <= 1:
        return False
    names = {_extract_tool_name(tc) for tc in independent}
    # 含冷启动敏感工具 → 串行（避免 GIL 下并发 import 竞争）
    if names & _COLD_START_SENSITIVE_TOOLS:
        return False
    # 全是快工具（只读小操作）→ 串行（省线程池开销）
    if names and names.issubset(_READONLY_TOOLS):
        return False
    # 其余（含慢工具/写工具/子进程）→ 并行有收益
    return True


def _extract_tool_name(tool_call: dict) -> str:
    """从 tool_call 字典提取工具名"""
    fn = tool_call.get("function", {})
    if hasattr(fn, "name"):
        return fn.name
    if isinstance(fn, dict):
        return fn.get("name", "")
    return ""


def _has_dependency(tool_call: dict, all_calls: list[dict]) -> bool:
    """判断当前工具是否依赖其他工具先执行"""
    name = _extract_tool_name(tool_call)
    if not name or name not in _TOOL_DEPENDENCIES:
        return False
    deps = _TOOL_DEPENDENCIES[name]
    for other in all_calls:
        other_name = _extract_tool_name(other)
        if other_name in deps:
            return True
    return False


def execute_tools_parallel(tool_calls: list[dict], execute_fn) -> list[dict]:
    """
    并行执行独立的工具调用

    Args:
        tool_calls: LLM 返回的工具调用列表
        execute_fn: 单个工具执行函数，签名为 (name, args) -> str

    Returns:
        与 tool_calls 顺序一致的结果列表，每个元素为 {"tool_call_id": str, "content": str}
    """
    if len(tool_calls) <= 1:
        # 单个或零个工具，直接串行
        results = []
        for tc in tool_calls:
            name = _extract_tool_name(tc)
            args = _parse_tool_args(tc)
            try:
                content = _execute_with_watchdog(execute_fn, name, args)
            except Exception as e:
                content = f"❌ 工具执行失败: {e}"
            results.append({"tool_call_id": tc.get("id", ""), "content": content})
        return results

    # 分离独立工具和依赖工具
    independent: list[dict] = []
    dependent: list[dict] = []
    for tc in tool_calls:
        if _has_dependency(tc, tool_calls):
            dependent.append(tc)
        else:
            independent.append(tc)

    results_map: dict[str, str] = {}

    # ⭐ 建议A：耗时门槛——只在真正有收益时才并行
    if independent and _should_parallel(independent):
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(independent))) as pool:
            future_to_tc = {}
            for tc in independent:
                name = _extract_tool_name(tc)
                args = _parse_tool_args(tc)
                future = pool.submit(_safe_execute, execute_fn, name, args)
                future_to_tc[future] = tc
            try:
                for future in concurrent.futures.as_completed(future_to_tc, timeout=TOOL_WATCHDOG_TIMEOUT):
                    tc = future_to_tc[future]
                    try:
                        results_map[tc.get("id", "")] = future.result()
                    except Exception as e:
                        results_map[tc.get("id", "")] = f"❌ 工具执行失败: {e}"
            except concurrent.futures.TimeoutError:
                logger.warning(f"⏱ 并行工具执行超过 {TOOL_WATCHDOG_TIMEOUT}s，看门狗中断")
                for future, tc in future_to_tc.items():
                    if tc.get("id", "") not in results_map:
                        results_map[tc.get("id", "")] = (
                            f"❌ 工具执行超时（>{TOOL_WATCHDOG_TIMEOUT}s），已强制中断。"
                            f"请检查卡死命令（SSH/网络/构建），拆解步骤后重试。"
                        )
    elif independent:
        # 不值得并行（快工具/冷启动敏感）→ 串行，省线程池开销
        for tc in independent:
            name = _extract_tool_name(tc)
            args = _parse_tool_args(tc)
            try:
                results_map[tc.get("id", "")] = _execute_with_watchdog(execute_fn, name, args)
            except Exception as e:
                results_map[tc.get("id", "")] = f"❌ 工具执行失败: {e}"

    # 串行执行依赖工具
    for tc in dependent:
        name = _extract_tool_name(tc)
        args = _parse_tool_args(tc)
        try:
            results_map[tc.get("id", "")] = execute_fn(name, args)
        except Exception as e:
            results_map[tc.get("id", "")] = f"❌ 工具执行失败: {e}"

    # 按原始顺序返回
    return [{"tool_call_id": tc.get("id", ""), "content": results_map.get(tc.get("id", ""), "")}
            for tc in tool_calls]


def _parse_tool_args(tool_call: dict) -> dict:
    """解析工具参数"""
    fn = tool_call.get("function", {})
    if hasattr(fn, "arguments"):
        args_str = fn.arguments
    elif isinstance(fn, dict):
        args_str = fn.get("arguments", "{}")
    else:
        args_str = "{}"
    try:
        return json.loads(args_str) if isinstance(args_str, str) else args_str
    except json.JSONDecodeError:
        return {}


def _safe_execute(execute_fn, name: str, args: dict) -> str:
    """安全执行工具，捕获异常"""
    try:
        return execute_fn(name, args)
    except Exception as e:
        logger.warning(f"工具 {name} 执行异常: {e}")
        return f"❌ 工具执行失败: {e}"


# ⭐ 看门狗：单工具执行超时保护（默认 10 分钟）
# 防止某个工具（如 SSH/网络/构建脚本）卡死时，整个 agent 循环挂起数十分钟
TOOL_WATCHDOG_TIMEOUT = 600


def _execute_with_watchdog(execute_fn, name: str, args: dict, timeout: int = TOOL_WATCHDOG_TIMEOUT) -> str:
    """带看门狗的单工具执行：超时立即返回提示，不阻塞 agent 循环。

    说明：Python 无法强制终止线程，超时后底层线程仍在后台运行（daemon 线程，
    进程退出不阻塞），但主流程立刻返回，agent 循环继续，杜绝"工具卡死 15 分钟"。
    """
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="tool_watchdog")
    future = pool.submit(_safe_execute, execute_fn, name, args)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        logger.warning(f"⏱ 工具 {name} 执行超过 {timeout}s，看门狗中断（后台线程已脱离，不再阻塞）")
        pool.shutdown(wait=False)
        return (f"❌ 工具执行超时（>{timeout}s），已强制中断该调用。"
                f"请检查是否存在卡死命令（SSH/网络/构建/等待输入），拆解步骤或缩短操作后重试。")
    except Exception as e:
        pool.shutdown(wait=False)
        return f"❌ 工具执行失败: {e}"


# ============================================================
# ⭐6 优先引导 file_replace
# ============================================================

_FILE_REPLACE_HINT = """
⚠️ 代码修改提示：小改动（≤5 处）优先用 file_replace，大改动（重写函数/类）才用 write_file
- file_replace: 精准替换，保留文件其余部分，token 消耗低
- write_file: 全量重写，适合大改动，但会发送整个文件内容
"""

_CODE_MODE_GUIDE = """
【高效率编码工作流 — 请严格遵守】

## 1. 定位代码
- 先用 grep_code 搜索关键词 → 找到目标文件
- 再用 read_file_content 读取具体文件（可同时读多个文件节省时间）

## 2. 理解上下文
- 用 list_functions 查看文件结构（函数/类列表）
- 用 analyze_imports 了解依赖关系
- 用 go_to_definition 跟踪定义

## 3. 执行修改
- ≤5 行小改：用 file_replace（高精度、低成本）
- 整个函数/类重写：用 write_file
- 跨文件批量：先规划所有改动，再逐一执行

## 4. 验证修改（必须执行！）
- 改完用 py_compile 或 run_command 验证是否可编译
- 如果有测试，用 run_tests 验证不破坏已有功能
- 用 git_diff 查看改动内容，确保没有误改

## 5. 质量检查
- 用 analyze_error 分析任何编译/运行时错误
- 用 get_diagnostics 检查代码质量问题
- 用 organize_imports 整理导入
- 用 format_code 格式化代码

## 核心原则
✅ 读文件可以并行（多个 read_file_content 同时调用）
✅ 改文件必须顺序（写完一个验证后再写下一个）
✅ 每次改动后都要验证——积少成多的 bug 最难找
✅ 优先用精准工具（file_replace > write_file, grep_code > find_files）
"""

_CODE_TOOLS_REFERENCE = """
【可用编程工具速查】

▸ 搜索: grep_code(全文) | find_files(文件名) | find_references(符号引用)
▸ 阅读: read_file_content | list_functions(结构) | analyze_imports(依赖)
▸ LSP:  go_to_definition | get_diagnostics | get_completions | find_all_references
▸ 编辑: file_replace(小改) | write_file(重写) | rename_symbol(重命名)
▸ 验证: run_command(编译) | run_tests(测试) | git_diff(变更) | git_status(状态)
▸ 调试: analyze_error(解释) | analyze_log(日志) | diagnose_crash(崩溃)
▸ 质量: format_code | organize_imports | code_review_file | security_scan_file
▸ Git:  git_status/diff/log/commit/add/push/pull/branch/checkout
▸ 性能: benchmark_function | profile_code_block | check_memory
▸ 终端: run_command(Shell) | run_build | install_deps | check_env
▸ 文档: generate_docstring | generate_readme | analyze_api_routes
▸ 测试: run_tests | run_coverage | discover_tests | generate_test_template
▸ DB:   explore_db | query_db | generate_model
▸ API:  http_request | test_api_endpoint | openapi_explore
▸ 重构: extract_function | analyze_imports
▸ 依赖: check_dependencies | detect_circular_imports | check_outdated
▸ CI:   generate_ci_config | generate_changelog | bump_version
▸ 配置: manage_env | scan_secrets | generate_env_template
▸ 片段: save_snippet | search_snippets | get_snippet
"""


def get_file_replace_hint() -> str:
    """获取 file_replace 使用提示"""
    return _FILE_REPLACE_HINT


# ============================================================
# ⭐7 增量测试
# ============================================================

def find_affected_tests(changed_files: list[str], project_root: str = ".") -> list[str]:
    """
    根据变更的文件找出受影响的测试文件

    策略：
    1. 如果变更的是测试文件本身，直接加入
    2. 如果变更的是源文件，查找同名的测试文件（test_*.py / *_test.py）
    3. 如果变更的是 __init__.py 或 conftest.py，查找同目录下所有测试
    """
    if not changed_files:
        return []

    affected: set[str] = set()
    root = Path(project_root)

    for file_path in changed_files:
        p = Path(file_path)
        # 相对路径转绝对
        if not p.is_absolute():
            p = root / p

        # 情况 1：本身就是测试文件
        if _is_test_file(p.name):
            if p.exists():
                affected.add(str(p))
            continue

        # 情况 2：源文件 → 找对应测试文件
        # 例如 src/module/foo.py → tests/test_foo.py 或 tests/module/test_foo.py
        test_patterns = [
            f"test_{p.stem}.py",
            f"{p.stem}_test.py",
        ]
        # 在常见测试目录中搜索
        for test_dir in ["tests", "test", "Tests", "TEST"]:
            test_root = root / test_dir
            if not test_root.exists():
                continue
            for pattern in test_patterns:
                for match in test_root.rglob(pattern):
                    affected.add(str(match))

        # 情况 3：__init__.py / conftest.py → 同目录所有测试
        if p.name in ("__init__.py", "conftest.py"):
            parent = p.parent
            for test_file in parent.rglob("test_*.py"):
                affected.add(str(test_file))
            for test_file in parent.rglob("*_test.py"):
                affected.add(str(test_file))

    return sorted(affected)


def _is_test_file(filename: str) -> bool:
    """判断是否为测试文件"""
    return (filename.startswith("test_") or filename.endswith("_test.py")) and filename.endswith(".py")


def build_incremental_test_cmd(base_cmd: list[str], changed_files: list[str], project_root: str = ".") -> list[str]:
    """
    构建增量测试命令

    Args:
        base_cmd: 原始测试命令，如 ["pytest", "tests/"]
        changed_files: 变更的文件列表
        project_root: 项目根目录

    Returns:
        优化后的测试命令
    """
    affected = find_affected_tests(changed_files, project_root)
    if not affected:
        return base_cmd

    # 如果找到了受影响的测试，替换测试路径
    # 例如 ["pytest", "tests/"] → ["pytest", "tests/test_foo.py", "tests/test_bar.py"]
    new_cmd = []
    for arg in base_cmd:
        if arg in ("tests/", "tests", "test/", "test"):
            new_cmd.extend(affected)
        else:
            new_cmd.append(arg)
    return new_cmd


# ============================================================
# ⭐8 自动注入工作区状态
# ============================================================

def get_workspace_status(project_root: str = ".", max_chars: int = 200) -> str:
    """
    获取轻量级工作区状态（git status --short）

    Returns:
        格式化的状态字符串，如果无变更或超过 max_chars 则返回空
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ""
        status = result.stdout.strip()
        if not status:
            return ""
        if len(status) > max_chars:
            # 截断并统计
            lines = status.split("\n")
            return f"📋 工作区变更 ({len(lines)} 个文件):\n" + "\n".join(lines[:10]) + f"\n... 等 {len(lines)} 个文件"
        return f"📋 工作区变更:\n{status}"
    except Exception:
        return ""


# ============================================================
# ⭐9 历史对话按类型过滤
# ============================================================

def filter_history_by_mode(history: list[dict], task_mode: str) -> list[dict]:
    """
    根据任务模式过滤历史对话，保留相关上下文

    Args:
        history: 完整历史消息列表
        task_mode: 当前任务模式 (code / game_publish / general)

    Returns:
        过滤后的历史消息列表
    """
    if not history or task_mode == "general":
        return history

    # 定义各模式的关键词
    mode_keywords = {
        "code": [
            "代码", "bug", "修复", "重构", "函数", "类", "报错", "错误",
            "refactor", "debug", "fix", "implement", "python", "def ", "class ",
            "git", "commit", "push", "pull", "branch", "merge",
            "test", "pytest", "unittest", "coverage",
            "file_replace", "write_file", "read_file", "grep", "find_",
        ],
        "game_publish": [
            "发布", "publish", "游戏", "game", "下载", "download",
            "截图", "screenshot", "logo", "简介", "oss", "上传",
            "browse", "网页", "页面", "链接",
        ],
    }

    keywords = mode_keywords.get(task_mode, [])
    if not keywords:
        return history

    # 保留最近 10 条 + 与当前模式相关的历史
    recent = history[-10:] if len(history) > 10 else history[:]
    older = history[:-10] if len(history) > 10 else []

    # 过滤旧历史：保留包含关键词的，或工具调用/结果（保持上下文连贯）
    filtered_older = []
    for msg in older:
        content = msg.get("content", "")
        role = msg.get("role", "")
        # 保留工具调用和结果（保持上下文）
        if role in ("tool", "assistant") and msg.get("tool_calls"):
            filtered_older.append(msg)
            continue
        # 检查是否包含关键词
        if any(kw in content for kw in keywords):
            filtered_older.append(msg)
            continue
        # 保留 user 消息（可能是任务切换点）
        if role == "user":
            filtered_older.append(msg)

    return filtered_older + recent


# ============================================================
# ⭐10 启用上下文压缩
# ============================================================

def should_compress_context(total_tokens: int, threshold: int = 20000) -> bool:
    """判断是否需要压缩上下文"""
    return total_tokens > threshold


def compress_context(ctx, model=None) -> str:
    """
    压缩上下文，返回摘要

    Args:
        ctx: ContextManager 实例
        model: LLM 模型（可选，用于 AI 摘要）

    Returns:
        摘要文本
    """
    if not hasattr(ctx, "summarize"):
        return ""
    try:
        return ctx.summarize(model=model)
    except Exception as e:
        logger.warning(f"上下文压缩失败: {e}")
        return ""


# ============================================================
# 综合工具函数
# ============================================================

def get_optimized_system_prompt_addition(task_mode: str) -> str:
    """
    根据任务模式获取系统提示词补充内容

    Returns:
        针对特定模式的提示词补充
    """
    if task_mode == "code":
        return _FILE_REPLACE_HINT + _CODE_MODE_GUIDE + _CODE_TOOLS_REFERENCE
    elif task_mode == "game_publish":
        return """
【游戏发布模式】
- 使用 browse_page / find_download_links 采集资源
- 发布前必须 check_content_quality 和 check_sensitive_words
- 图片使用 oss_upload 上传到云存储
"""
    return ""
