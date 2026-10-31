# -*- coding: utf-8 -*-
"""工具执行入口 — agent_loop 使用。

所有工具调用（并行路径和看门狗路径）最终都汇聚到这里的 _execute_tool_optimized，
因此把「资源排队」放在这一处就够了，不用去改 browser_tools / registry（两者在
完整性清单里）。

冲突来源（tools/concurrency_probe.py 实测）：
    · browser_tools 的 _source_view / _admin_view / _active_ctx 是模块级变量，
      4/4 个跨线程同一实例；Worker A 设 source、B 设 admin 后，A 下一次操作
      看到的是 admin —— 操作了错误窗口且不报错。
    · desktop_bot 插件无任何 Lock，鼠标键盘只有一套。
    · 同一文件读-改-写 8 线程 × 40 轮丢 97% 更新。
    · 同一仓库并发 git 写 17/24 次撞 index.lock。

策略：
    浏览器 / 桌面 / 相机 —— Worker 内首次使用时申请【粘性】租约，一直占到
    Worker 结束。因为 _active_ctx 这类状态是跨调用残留的，只给单次调用加锁不够。
    文件 / git           —— 按绝对路径排队，粒度到具体文件/仓库。
    主 Agent（无 Worker） —— 每次调用单独申请，用完即放。
"""
from __future__ import annotations

import os

from ..tools.registry import execute_tool, TOOL_REGISTRY
from .agent_optimizer import execute_tools_parallel
from ..utils import resource_lease as _lease
from ..utils import exec_context as _ec

__all__ = ["_execute_tool_optimized", "resource_of", "lease_status"]

# 独占型资源：一旦占用，整段时间内别人不能碰（状态会跨调用残留）
_STICKY_CATEGORIES = {"browser", "desktop", "camera"}

# 写类文件工具 —— 需要按路径排队
_FILE_WRITE_TOOLS = {
    "write_file", "delete_file", "file_replace", "compress_image",
    "rename_symbol", "format_code", "organize_imports", "generate_docstring",
    "generate_readme", "save_snippet", "manage_env", "generate_env_template",
    "generate_ci_config", "generate_changelog", "bump_version",
}

# 会改 git 索引的工具 —— 同一仓库内必须串行
_GIT_WRITE_PREFIX = ("git_add", "git_commit", "git_reset", "git_checkout",
                     "git_stash", "git_tag", "git_init", "git_pull", "git_push",
                     "git_clone", "git_branch")

_PATH_ARG_NAMES = ("path", "filepath", "file_path", "local_path", "output_path",
                   "target", "dest", "directory", "repo_path", "project_root")

# 等待上限（秒）—— 分两类，等的对象不同：
#   独占类（browser / desktop / camera）：等的是【执行者之间的争用】。
#       120s 太长，界面上看起来像卡死；60s 足够，超时就 fail-closed 报繁忙。
#   路径类（file:<路径> / git:<仓库>）：等的是【同一目标上的写锁】。
#       git clone/push 本身就可能跑几分钟，等的一方只给 60s 会误判繁忙，保持 120s。
_EXCLUSIVE_TIMEOUT = 60.0
_PATH_TIMEOUT = 120.0
_DEFAULT_TIMEOUT = _EXCLUSIVE_TIMEOUT     # 向后兼容旧引用


def _timeout_for(res: str) -> float:
    """独占资源等 60s，路径锁等 120s。"""
    return _PATH_TIMEOUT if str(res).startswith(("file:", "git:")) else _EXCLUSIVE_TIMEOUT


def _abs_or_empty(v, base=""):
    if not v or not isinstance(v, str):
        return ""
    try:
        p = v if os.path.isabs(v) else os.path.join(base or os.getcwd(), v)
        return os.path.normcase(os.path.abspath(p))
    except (OSError, ValueError):
        return ""


def resource_of(name: str, args: dict):
    """判断一次工具调用需要哪种资源。返回 (资源名, 是否粘性)；不需要则 (None, False)。"""
    if not name:
        return None, False

    # 1) 按注册表 category 判（browser / desktop / camera 这类独占硬件）
    tool = TOOL_REGISTRY.get(name)
    cat = getattr(tool, "category", "") or ""
    if cat in _STICKY_CATEGORIES:
        return cat, True

    # 2) 插件类工具按名字前缀判（desktop_bot / camera_bot 不在 registry.category 里）
    if name.startswith(("desktop_", "screen_", "mouse_", "keyboard_")):
        return "desktop", True
    if name.startswith(("camera_", "vision_capture")):
        return "camera", True

    # 3) git 写操作：按仓库根排队
    if name.startswith(_GIT_WRITE_PREFIX):
        args = args or {}
        base = args.get("repo_path") or args.get("project_root") or os.getcwd()
        root = _abs_or_empty(base) or os.path.normcase(os.getcwd())
        return f"git:{root}", False

    # 4) 文件写：按目标路径排队（多参数时取第一个存在的）
    if name in _FILE_WRITE_TOOLS:
        args = args or {}
        for key in _PATH_ARG_NAMES:
            p = _abs_or_empty(args.get(key))
            if p:
                return f"file:{p}", False

    return None, False


def _execute_tool_optimized(name: str, args: dict) -> str:
    """单个工具执行（带资源排队），供 execute_tools_parallel 调用。"""
    res, sticky = resource_of(name, args)
    if not res:
        return execute_tool(name, args)

    owner = _ec.owner()
    # 主 Agent 不持有粘性租约（它没有 release_all 的时机，粘住就是泄漏）
    if not _ec.is_worker():
        sticky = False

    timeout = _timeout_for(res)

    try:
        with _lease.guard(res, owner, timeout=timeout, sticky=sticky):
            return execute_tool(name, args)
    except _lease.LeaseTimeout as e:
        return (
            f"🚫 资源繁忙，本次未执行：{name}\n"
            f"   {e}\n"
            f"   当前占用情况：{_lease.status()}\n"
            f"   这不是命令出错，是排队超时（上限 {timeout:.0f}s）。稍后重试，或等占用方结束。"
        )


def lease_status() -> dict:
    """诊断用：当前资源占用情况。"""
    return _lease.status()
