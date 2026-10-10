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
]

_lock = threading.RLock()
_signals: list = []


class AbortedError(Exception):
    """协作式中止异常（用户终止任务）。"""

    def __init__(self, reason: str = "user_aborted"):
        self.reason = reason
        super().__init__(reason)


def register(signal) -> None:
    """注册一个中止信号（threading.Event / AbortSignal 均可）。

    ⚠️ 自愈逻辑（2026-09-28 修复）：
        register / unregister 由 track_abort 上下文管理器成对调用。
        但若承载任务的线程或生成器没有正常收尾（daemon 线程被遗弃、
        主循环未退出等），unregister 就永远不会执行，该信号（通常已是
        set 状态）会永久滞留在全局 _signals 中。
        由于 is_aborted() 的语义是「任一信号 set 即判定中止」，
        一个僵尸信号便会毒化其后【所有任务的所有工具】：
        用户只中止一次，之后每个工具都返回「已中止」，直到重启进程。

        因此这里做两步自愈：
          ① 清理其他已 set 的历史信号（它们已完成使命，不再具约束力）；
          ② 若传入信号本身已 set（旧对象被复用/上轮残留），复位之。
        这样任何新任务都能从干净的中止状态开始，不再被旧信号连坐。
    """
    if signal is None:
        return
    with _lock:
        # ① 清理僵尸信号：已触发中止的历史信号不再参与判定
        for s in list(_signals):
            if s is signal:
                continue
            try:
                if s.is_set():
                    _signals.remove(s)
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
        for s in _signals:
            if s is signal:
                return
        _signals.append(signal)


def reset() -> int:
    """强制清空所有已登记的中止信号，返回被清除的信号数量。

    供「新任务开始 / 异常兜底」等场合彻底复位中止状态使用。
    """
    with _lock:
        n = len(_signals)
        _signals.clear()
        return n


def unregister(signal) -> None:
    """注销中止信号（任务结束时必须调用，防止跨任务误判）。"""
    if signal is None:
        return
    with _lock:
        for i, s in enumerate(_signals):
            if s is signal:
                del _signals[i]
                return


def _snapshot() -> list:
    with _lock:
        return list(_signals)


def is_aborted() -> bool:
    """当前是否有任一已注册信号处于「已中止」状态。"""
    for s in _snapshot():
        try:
            if s.is_set():
                return True
        except Exception:
            continue
    return False


def abort_reason(default: str = "user_aborted") -> str:
    """取中止原因码（user_aborted / timeout / disconnected / concurrent）。"""
    for s in _snapshot():
        try:
            if s.is_set():
                return getattr(s, "reason", default)
        except Exception:
            continue
    return default


def check_abort() -> None:
    """已中止则抛 AbortedError；供工具长循环调用。"""
    if is_aborted():
        raise AbortedError(abort_reason())


class track_abort:
    """上下文管理器：任务期间注册 / 注销中止信号。

    用法::

        with track_abort(abort_event):
            run_agent_loop(...)
    """

    def __init__(self, signal):
        self._signal = signal

    def __enter__(self):
        register(self._signal)
        return self._signal

    def __exit__(self, exc_type, exc, tb):
        unregister(self._signal)
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
