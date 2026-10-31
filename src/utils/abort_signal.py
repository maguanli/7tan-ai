"""协作式中止信号 —— 让「正在执行的长任务」能被用户中止。

背景（2026-09-26 修复的真 BUG）：
    用户点「终止任务」后，只停得掉「模型正在说话」这一段；
    工具一旦开始执行（例如长达 143 秒的桌面粘贴循环），中间没有任何中止检查点，
    会一路跑完。根因是：工具执行层（tool_executor / agent_optimizer）从不检查中止信号，
    子进程执行器（run_command / desktop_*）用的也是 subprocess.run(timeout=...)——
    只认超时，不认中止。

本模块提供协作式中止的三个能力：
    1. 注册/注销当前任务的中止信号（agent_loop 在任务开始时注册）；
    2. 工具侧轮询感知：is_aborted() / check_abort()；
    3. 子进程执行：run_with_abort()——中止时立即杀掉整个进程树。

── 2026-11-01 改造：中止信号按作用域隔离（多 Agent 前置） ────────────
    改造前的实现是「一个模块级 list，任一信号 set 即判中止」，有两个真问题：

    问题一（并发连坐）：A、B 两个任务同时跑，用户中止 A，
            由于 is_aborted() 是「任一为真即为真」，B 的工具也会以为该停。
            Worker B 会莫名其妙地在半路退出，而且日志上看起来像是自己要停。

    问题二（嵌套污染，更隐蔽）：主 Agent 派一个 Worker 出去干活，
            两者在同一个线程同步执行。Worker 因超时把【自己的】abort_event 置位后，
            主 Agent 接下来调用的每个工具都会看到 is_aborted()=True，
            于是主 Agent 也停了——用户看到的现象是「派了个子任务，结果我自己也被终止了」。

    改法：_signals 从「一个 list」改成「按作用域分组」，作用域默认取当前线程；
    并且 is_aborted() 只看该作用域里【最后注册】的那个信号（栈顶语义），
    内层任务的信号注销后，外层自然恢复，不再互相污染。

        主 Agent 注册 sig_main        scope=主线程  [sig_main]
        Worker 注册   sig_w           scope=主线程  [sig_main, sig_w]   ← is_aborted 只看 sig_w
        Worker 超时   sig_w.set()     → 只影响 sig_w，主 Agent 不受影响
        Worker 注销   sig_w           scope=主线程  [sig_main]          ← 主 Agent 恢复原判定

    跨线程时（P1 并发化：每个 Worker 跑在 TaskQueue 的独立线程里），
    各线程作用域天然分离，无需额外处理。

注意：这是「协作式」中止。Python 无法强杀线程，所以需要工具主循环
主动调用 is_aborted()/check_abort() 才能及时退出；子进程则可被强制杀掉。
"""
from __future__ import annotations

import platform
import subprocess
import threading
import time

__all__ = [
    "AbortedError",
    "register",
    "unregister",
    "reset",
    "is_aborted",
    "abort_reason",
    "check_abort",
    "track_abort",
    "run_with_abort",
    "kill_tree",
    "current_scope",
    "scope_stats",
]

_lock = threading.RLock()
# 作用域 -> 信号栈。作用域默认是线程 ident（int）；也可传任意可哈希值
# （如 "session-xxx"）以便将来按会话隔离。
_signals: dict = {}

# 当前作用域为空时，是否回落到主线程的作用域。
# 用途：GUI 的「终止」按钮是在主线程置位全局信号的，工作线程里若没注册
# 自己的信号，仍应能感知到用户的全局中止意图。
_INHERIT_MAIN = True


class AbortedError(Exception):
    """协作式中止异常（用户终止任务）。"""

    def __init__(self, reason: str = "user_aborted"):
        self.reason = reason
        super().__init__(reason)


def current_scope():
    """当前作用域标识（默认 = 当前线程 ident）。"""
    return threading.get_ident()


def _resolve_scope(scope):
    return current_scope() if scope is None else scope


def _stack(scope):
    """取某作用域的信号栈（副本）。"""
    with _lock:
        return list(_signals.get(scope) or [])


def _snapshot(scope=None):
    """兼容旧接口：无参时返回当前作用域的信号栈副本。"""
    return _stack(_resolve_scope(scope))


def register(signal, scope=None) -> None:
    """注册一个中止信号（threading.Event / AbortSignal 均可）。

    多个信号按注册顺序入栈，is_aborted() 只看栈顶（最后一个）。
    这样「内层任务」的信号不会盖住「外层任务」，注销后外层即恢复。

    ⚠️ 自愈逻辑（2026-09-28 增加，2026-11-01 收紧作用域）：
        若承载任务的线程或生成器没有正常收尾（daemon 线程被遗弃、
        主循环未退出等），unregister 就永远不会执行，该信号会滞留在栈里。
        原实现会在【所有】信号中清理已 set 的僵尸，这会把别的任务正在用的
        信号一起清掉；现在只清理【本作用域】里的僵尸，不跨作用域动手。
    """
    if signal is None:
        return
    sc = _resolve_scope(scope)
    with _lock:
        stack = _signals.setdefault(sc, [])

        # ① 清理本作用域的僵尸信号：已触发中止的历史信号不再参与判定
        for s in list(stack):
            if s is signal:
                continue
            try:
                if s.is_set():
                    stack.remove(s)
            except Exception:
                pass

        # ② 复位被复用的旧信号对象（新任务不应继承旧的中止态）
        try:
            if hasattr(signal, "is_set") and signal.is_set():
                if hasattr(signal, "clear"):
                    signal.clear()
                elif hasattr(signal, "_event"):
                    signal._event.clear()
        except Exception:
            pass

        # ③ 去重登记
        for s in stack:
            if s is signal:
                return
        stack.append(signal)


def reset() -> int:
    """强制清空所有作用域的中止信号，返回被清除的信号数量。"""
    with _lock:
        n = sum(len(v) for v in _signals.values())
        _signals.clear()
        return n


def unregister(signal, scope=None) -> None:
    """注销中止信号（任务结束时必须调用，防止跨任务误判）。"""
    if signal is None:
        return
    sc = _resolve_scope(scope)
    with _lock:
        stack = _signals.get(sc)
        if not stack:
            return
        for i, s in enumerate(stack):
            if s is signal:
                del stack[i]
                break
        if not stack:
            _signals.pop(sc, None)


def _top_is_set(scope) -> bool:
    stack = _stack(scope)
    if not stack:
        return False
    try:
        return bool(stack[-1].is_set())
    except Exception:
        return False


def _top_reason(scope, default: str) -> str:
    stack = _stack(scope)
    if not stack:
        return default
    try:
        return getattr(stack[-1], "reason", default)
    except Exception:
        return default


def _candidate_scopes(scope=None):
    """待检查的作用域顺序：自己优先，其次（可选）主线程。"""
    if scope is not None:
        return [_resolve_scope(scope)]
    scopes = [current_scope()]
    if _INHERIT_MAIN:
        try:
            main = threading.main_thread().ident
        except Exception:
            main = None
        if main is not None and main not in scopes:
            scopes.append(main)
    return scopes


def is_aborted(scope=None) -> bool:
    """当前作用域是否有已注册信号处于「已中止」状态。

    只判【第一个非空作用域】的栈顶信号，不再做「任一为真即为真」的全域扫描。
    没有作用域参数时：先看当前线程，当前线程没有信号才回落到主线程。
    """
    for sc in _candidate_scopes(scope):
        if _stack(sc):
            return _top_is_set(sc)
    return False


def abort_reason(default: str = "user_aborted") -> str:
    """取中止原因码（user_aborted / timeout / disconnected / concurrent）。"""
    for sc in _candidate_scopes(None):
        if _stack(sc):
            return _top_reason(sc, default)
    return default


def check_abort() -> None:
    """已中止则抛 AbortedError；供工具长循环调用。"""
    if is_aborted():
        raise AbortedError(abort_reason())


def scope_stats() -> dict:
    """诊断用：各作用域当前注册了几个信号、栈顶是否已中止。"""
    with _lock:
        out = {}
        for sc, stack in _signals.items():
            top = stack[-1] if stack else None
            try:
                aborted = bool(top.is_set()) if top is not None else False
            except Exception:
                aborted = False
            out[sc] = {"count": len(stack), "aborted": aborted}
        return out


class track_abort:
    """上下文管理器：任务期间注册 / 注销中止信号。

    用法::

        with track_abort(abort_event):
            run_agent_loop(...)

        # 需要显式指定作用域时（例如按会话隔离）
        with track_abort(abort_event, scope=f"session-{sid}"):
            ...
    """

    def __init__(self, signal, scope=None):
        self._signal = signal
        self._scope = scope

    def __enter__(self):
        register(self._signal, self._scope)
        return self._signal

    def __exit__(self, exc_type, exc, tb):
        unregister(self._signal, self._scope)
        return False


# ── 子进程执行：中止即杀进程树 ────────────────────────────────

def kill_tree(proc) -> None:
    """强制杀掉子进程及其整棵进程树（Windows 用 taskkill /T，类 Unix 用 killpg）。"""
    if proc is None:
        return
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            import os
            import signal as _signal
            os.killpg(os.getpgid(proc.pid), _signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_with_abort(cmd, cwd=None, timeout=None, env=None, poll: float = 0.2):
    """执行子进程，并在用户中止时立即杀掉它。

    Args:
        cmd: 命令列表
        cwd: 工作目录
        timeout: 超时秒数（None=不限）
        env: 环境变量
        poll: 中止检测轮询间隔（秒）

    Returns:
        (returncode, stdout, stderr)

    Raises:
        AbortedError: 用户中止
        subprocess.TimeoutExpired: 超时
    """
    kwargs = {
        "cwd": cwd,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if env is not None:
        kwargs["env"] = env
    if platform.system() == "Windows":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    deadline = (time.time() + timeout) if timeout else None

    while True:
        if is_aborted():
            kill_tree(proc)
            try:
                proc.communicate(timeout=5)
            except Exception:
                pass
            raise AbortedError(abort_reason())

        wait = poll
        if deadline is not None:
            wait = min(poll, max(0.0, deadline - time.time()))
        try:
            out, err = proc.communicate(timeout=wait)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            if deadline is not None and time.time() >= deadline:
                kill_tree(proc)
                try:
                    proc.communicate(timeout=5)
                except Exception:
                    pass
                raise subprocess.TimeoutExpired(cmd, timeout)
            continue
