"""
代码修改事件总线 — AI 文件修改 → UI 实时变更面板

发布端（工具层，任意线程）:
    publish_file_change(action, path, old_text=None, new_text=None,
                        diff_text=None, summary="")

消费端（UI 主线程，QTimer 轮询）:
    drain_changes(max_items) -> list[dict]

队列满时丢弃最旧记录，保证"最新修改"优先可见。
"""
from __future__ import annotations

import difflib
import queue
import threading
from datetime import datetime
from pathlib import Path

_change_queue: "queue.Queue[dict]" = queue.Queue(maxsize=1000)
_seq_lock = threading.Lock()
_seq = 0


def _next_seq() -> int:
    global _seq
    with _seq_lock:
        _seq += 1
        return _seq


def build_diff(old_text, new_text, path, context: int = 2):
    """生成 unified diff 文本。

    - old_text 为 None → 新建文件，返回 None
    - 无实际差异 → 返回 None
    """
    if old_text is None:
        return None
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    try:
        text = "".join(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{Path(path).as_posix()}",
            tofile=f"b/{Path(path).as_posix()}",
            lineterm="",
            n=context,
        ))
    except Exception:
        return None
    return text if text.strip() else None


def publish_file_change(action: str, path: str, old_text=None, new_text=None,
                        diff_text=None, summary: str = "") -> dict:
    """发布一次文件变更事件（线程安全，任意线程可调用）。

    action: write / replace / create / delete / config
    path:   文件路径
    old_text / new_text: 变更前后内容（文本模式），用于自动生成 diff
    diff_text: 预生成的 diff（可选，优先使用）
    summary: 一句话摘要（如 "替换 3 组字符串"）
    """
    if diff_text is None:
        diff_text = build_diff(old_text, new_text, path)
    now = datetime.now()
    rec = {
        "seq": _next_seq(),
        "ts": now.strftime("%H:%M:%S"),
        "ts_full": now.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "path": str(path),
        "diff": diff_text or "",
        "summary": summary or "",
    }
    try:
        _change_queue.put_nowait(rec)
    except queue.Full:
        # 队列满：丢弃最旧一条，保证最新修改优先可见
        try:
            _change_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            _change_queue.put_nowait(rec)
        except queue.Full:
            pass
    return rec


def drain_changes(max_items: int = 50) -> list:
    """批量拉取事件（UI 主线程调用，线程安全）。"""
    items = []
    try:
        while len(items) < max_items:
            items.append(_change_queue.get_nowait())
    except queue.Empty:
        pass
    return items


def pending_count() -> int:
    """当前待消费事件数"""
    return _change_queue.qsize()
