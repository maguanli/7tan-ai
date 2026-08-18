"""
主线程看门狗 — 检测 UI 假死并 dump 现场

原理:
  - 主线程 QTimer 每 1 秒更新 _heartbeat
  - 后台看门狗线程每 3 秒检查: 若 _heartbeat 超 10 秒未更新 → 判定主线程卡死
  - 卡死时用 sys._current_frames() dump 所有线程的 Python 栈到 logs/watchdog_dump_*.txt
  - 恢复心跳前只 dump 一次（防刷屏）

用法:
  watchdog.start()        # app 启动时调用（任意线程）
  watchdog.tick()         # 主线程 QTimer 每 1s 调用
  watchdog.stop()         # 退出时调用（可选）
"""
from __future__ import annotations

import sys
import time
import threading
import traceback
from pathlib import Path

_heartbeat = 0.0
_heartbeat_lock = threading.Lock()
_dumped = False
_dump_dir = None
_stop = threading.Event()

_TIMEOUT_SECONDS = 10      # 心跳超过 10 秒未更新 = 判定卡死
_CHECK_INTERVAL = 3.0      # 看门狗检查间隔
_TICK_INTERVAL = 1.0       # 主线程心跳间隔


def _logs_dir() -> Path:
    global _dump_dir
    if _dump_dir is None:
        _dump_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    return _dump_dir


def tick():
    """主线程心跳（QTimer 每 1s 调用）"""
    global _heartbeat, _dumped
    with _heartbeat_lock:
        _heartbeat = time.monotonic()
        # 心跳恢复 → 允许下次再次 dump
        _dumped = False


def _dump_stacks(reason: str):
    """dump 所有线程的 Python 栈"""
    try:
        _logs_dir().mkdir(parents=True, exist_ok=True)
        path = _logs_dir() / f"watchdog_dump_{int(time.time())}.txt"
        frames = sys._current_frames()
        lines = [
            f"=== 主线程卡死检测: {time.strftime('%Y-%m-%d %H:%M:%S')} ===",
            f"原因: {reason}",
            f"活跃线程数: {len(frames)}",
            "=" * 60,
        ]
        for tid, frame in frames.items():
            lines.append(f"\n--- 线程 {tid} ---")
            for fname, lineno, func, code in traceback.extract_stack(frame):
                lines.append(f"  {fname}:{lineno} in {func}")
                if code:
                    lines.append(f"      {code.strip()}")
            lines.append("")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[Watchdog] 主线程疑似卡死，栈已 dump 到 {path}")
    except Exception as e:
        print(f"[Watchdog] dump 失败: {e}")


def _watch_loop():
    """看门狗线程主循环"""
    global _dumped
    while not _stop.is_set():
        time.sleep(_CHECK_INTERVAL)
        try:
            with _heartbeat_lock:
                stale = (time.monotonic() - _heartbeat) > _TIMEOUT_SECONDS
                should_dump = stale and not _dumped
                if should_dump:
                    _dumped = True
            if should_dump:
                # 锁外 dump，避免持有锁时主线程尝试 tick 死锁
                _dump_stacks(
                    f"心跳超时 {_TIMEOUT_SECONDS}s（看门狗检查周期 {_CHECK_INTERVAL}s）"
                )
        except Exception:
            pass


def start():
    """启动看门狗（幂等）"""
    global _heartbeat
    with _heartbeat_lock:
        if _heartbeat == 0.0:
            _heartbeat = time.monotonic()
    t = threading.Thread(target=_watch_loop, name="main-thread-watchdog", daemon=True)
    t.start()
    return t


def stop():
    """停止看门狗"""
    _stop.set()
