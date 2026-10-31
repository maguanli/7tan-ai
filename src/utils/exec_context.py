# -*- coding: utf-8 -*-
"""执行上下文 —— 让「我属于哪个 Worker、根目录在哪」跟着任务走，而不是跟着线程走。

为什么需要它：
    2026-11-01 实测发现 agent_optimizer.execute_tools_parallel 会把同一轮里的
    多个工具丢进 ThreadPoolExecutor（max_workers=4）。而 cmd_scope 的作用域帧
    原本存在 threading.local 里，池线程看不到 → 越界命令被放行。

    实测证据（tools/probe_parallel_scope.py）：
        串行（主线程）  ✅ 拒绝   cwd 越界
        并行（池线程）  ⚠️ 放行   frame=None

    这不是「将来并发才有」的隐患：单个 Agent 一轮里并发调两个工具就会触发。

改法：
    把这个上下文放进 contextvars.ContextVar。在执行池提交任务时用
    contextvars.copy_context().run(...) 把上下文一起带过去 —— 这样池线程
    拿到的就是提交那一刻的上下文，而不是空的。

分层：
    exec_context  谁在干活（worker id / 根目录 / 是否严格）
    cmd_scope     在此上下文里的可嵌套作用域帧栈
    resource_lease 对此上下文可独占的物理资源（浏览器 / 桌面 / 文件 / git）
"""
from __future__ import annotations

import contextvars
import threading
import uuid

__all__ = [
    "ExecCtx",
    "current",
    "set_worker",
    "clear",
    "owner",
    "is_worker",
    "bind",
    "run_in_context",
]

_ctx: contextvars.ContextVar = contextvars.ContextVar("7tan_exec_ctx", default=None)
_fallback = threading.local()          # 兼容：完全没有上下文时也能取到 owner


class ExecCtx:
    """一次执行单元的上下文。immutable，避免被下游误改。"""

    __slots__ = ("worker_id", "cwd_root", "strict", "label")

    def __init__(self, worker_id: str, cwd_root: str = "", strict: bool = True,
                 label: str = ""):
        self.worker_id = worker_id
        self.cwd_root = cwd_root
        self.strict = bool(strict)
        self.label = label or worker_id

    def __repr__(self) -> str:
        return f"<ExecCtx {self.worker_id} root={self.cwd_root} strict={self.strict}>"


def current():
    """当前执行上下文；主 Agent（无 Worker）返回 None。"""
    return _ctx.get()


def set_worker(cwd_root: str = "", label: str = "", worker_id: str = "") -> ExecCtx:
    """进入 Worker 上下文。返回 ctx，退出时必须 clear()。"""
    wid = worker_id or f"w-{uuid.uuid4().hex[:8]}"
    ctx = ExecCtx(wid, cwd_root=str(cwd_root or ""), strict=True, label=label)
    _ctx.set(ctx)
    _fallback.owner = wid
    return ctx


def clear() -> None:
    _ctx.set(None)


def owner() -> str:
    """当前执行者标识。Worker 返回自己的 id；主 Agent 返回 'main'。

    用作资源租约的持有人：同一个 owner 重复申请同一资源视为重入，不互锁。
    """
    c = _ctx.get()
    if c is not None:
        return c.worker_id
    return getattr(_fallback, "owner", None) or "main"


def is_worker() -> bool:
    return _ctx.get() is not None


def bind(root: str = "", label: str = "", worker_id: str = ""):
    """同步上下文里的临时绑定（主线程直接调用 Worker 时用）。

    返回 ctx；调用方负责 clear()。用 ContextVar 的 token 做精确还原，
    避免嵌套时把外层的上下文一起抹掉。
    """
    wid = worker_id or f"w-{uuid.uuid4().hex[:8]}"
    ctx = ExecCtx(wid, cwd_root=str(root or ""), strict=True, label=label)
    tok = _ctx.set(ctx)
    prev_owner = getattr(_fallback, "owner", None)
    _fallback.owner = wid
    return ctx, tok, prev_owner


def unbind(tok, prev_owner=None) -> None:
    try:
        _ctx.reset(tok)
    except (ValueError, RuntimeError):
        _ctx.set(None)
    _fallback.owner = prev_owner


def run_in_context(fn, *args, **kwargs):
    """在当前上下文快照里执行 fn。

    线程池提交时用它包一层，池线程就能拿到提交那一刻的 ExecCtx 与作用域帧。
    """
    ctx = contextvars.copy_context()
    return ctx.run(fn, *args, **kwargs)
