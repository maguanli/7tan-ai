"""
代码修改事件总线 — AI 文件修改 → UI 实时变更面板

发布端（工具层，任意线程）:
    publish_file_change(action, path, old_text=None, new_text=None,
                        diff_text=None, summary="")

消费端（UI 主线程，QTimer 轮询）:
    drain_changes(max_items) -> list[dict]

v2: 事件同时持久化到 data/code_changes.jsonl（重启不丢），
    面板打开时可调用 load_history() 加载历史记录。
    队列满时丢弃最旧记录，保证"最新修改"优先可见。
v3: read_history_tail() 跨进程增量读取 jsonl —— 即使发布端与
    消费端不在同一进程（AI 工具调用 vs GUI），面板也能实时显示。
v4: seq 改为【全局唯一】（进程ID + 毫秒时间戳 + 自增序号）——
    修复跨进程/重启后 seq 从 1 重新计数，导致面板把新事件
    误判为"已存在"而去重丢弃（实时显示失效的根因）。
"""
from __future__ import annotations

import difflib
import json
import os
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

_change_queue: "queue.Queue[dict]" = queue.Queue(maxsize=1000)
_seq_lock = threading.Lock()
_seq = 0
# 本进程唯一前缀：进程ID + 启动时刻（毫秒）→ 跨进程/重启绝不重复
_PID = os.getpid()
_START_MS = int(time.time() * 1000)

_history_lock = threading.Lock()
_HISTORY_MAX = 300            # 历史文件保留条数
_HISTORY_MAX_BYTES = 5_000_000  # 5MB 上限
# v5: 单条 diff 体积上限 —— 防止写超大文件时 jsonl 出现 MB 级记录，
#    导致面板 UI 线程 400ms 轮询解析卡死（未响应的主要风险源）
_MAX_DIFF_CHARS = 120_000
_HISTORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "code_changes.jsonl"


def _next_seq() -> str:
    """生成全局唯一 seq（字符串）。

    v4: 旧版为进程内自增 int，多个进程/多次重启都会从 1 开始，
    导致面板按 seq 去重时把新事件误判为已存在而丢弃（实时失效）。
    新版："{pid}-{启动毫秒}-{自增}" 保证任何进程/重启后都唯一。
    """
    global _seq
    with _seq_lock:
        _seq += 1
        return f"{_PID}-{_START_MS}-{_seq}"


def build_diff(old_text, new_text, path, context: int = 2):
    """生成 unified diff 文本。

    - old_text 为 None（新建文件）→ 全部行显示为新增 (+)
    - new_text 为 None（删除文件）→ 全部行显示为删除 (-)
    - 两文本都为空/无差异 → 返回 None
    """
    if old_text is None and new_text is None:
        return None
    # 新建空文件：返回最小头部，让面板知道这是新建（避免显示"无差异"）
    if old_text is None and not (new_text or "").strip():
        return (f"--- a/{Path(path).as_posix()}\n"
                f"+++ b/{Path(path).as_posix()}\n"
                "@@ -0,0 +0,0 @@\n（空文件）")
    # 标准组合：splitlines() 不带 keepends + lineterm="" + join("\n")
    # （避免 header 行 ---/+++/@@ 粘连、内容行错位）
    old_lines = [] if old_text is None else old_text.splitlines()
    new_lines = [] if new_text is None else new_text.splitlines()
    try:
        text = "\n".join(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{Path(path).as_posix()}",
            tofile=f"b/{Path(path).as_posix()}",
            lineterm="",
            n=context,
        ))
    except Exception:
        return None
    return text if text.strip() else None


def _append_history(rec: dict):
    """事件追加到历史文件（线程安全，失败不影响内存队列）"""
    try:
        with _history_lock:
            _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            # 超限修剪（行数 or 体积）
            try:
                if _HISTORY_PATH.stat().st_size > _HISTORY_MAX_BYTES:
                    with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if len(lines) > _HISTORY_MAX:
                        with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
                            f.writelines(lines[-_HISTORY_MAX:])
            except Exception:
                pass
    except Exception:
        pass


def publish_file_change(action: str, path: str, old_text=None, new_text=None,
                        diff_text=None, summary: str = "", status: str = "ok") -> dict:
    """发布一次文件变更事件（线程安全，任意线程可调用）。

    action: write / replace / create / delete / config
    path:   文件路径
    old_text / new_text: 变更前后内容（文本模式），用于自动生成 diff
    diff_text: 预生成的 diff（可选，优先使用）
    summary: 一句话摘要（如 "替换 3 组字符串"）
    status: 操作状态 ok / failed / rolled_back（面板显示状态徽章，默认 ok）
    """
    if diff_text is None:
        diff_text = build_diff(old_text, new_text, path)
    # v5: diff 体积上限（在换行边界截断，保持可解析；显示端本就只渲染前 500 行）
    if diff_text and len(diff_text) > _MAX_DIFF_CHARS:
        cut = diff_text.rfind("\n", 0, _MAX_DIFF_CHARS)
        if cut <= 0:
            cut = _MAX_DIFF_CHARS
        diff_text = diff_text[:cut] + "\n…（diff 过长，已截断，完整内容请直接查看文件）"
    now = datetime.now()
    rec = {
        "seq": _next_seq(),
        "ts": now.strftime("%H:%M:%S"),
        "ts_full": now.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "path": str(path),
        "diff": diff_text or "",
        "summary": summary or "",
        "status": status or "ok",
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
    _append_history(rec)
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


def load_history(limit: int = 300) -> list:
    """加载历史记录（旧 → 新），用于面板打开时初始化。

    重启后事件不丢失；文件损坏时静默跳过坏行。
    """
    if not _HISTORY_PATH.exists():
        return []
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
    except Exception:
        return []
    recs = []
    for ln in lines:
        try:
            recs.append(json.loads(ln))
        except Exception:
            continue
    return recs


def history_path() -> Path:
    """历史文件路径（调试用）"""
    return _HISTORY_PATH


# ── v3: 跨进程增量读取（实时兜底）────────────────────────────
# AI 工具调用与 GUI 可能运行在不同进程时，内存队列无法跨进程共享。
# 但历史文件（jsonl）是共享的 —— 面板轮询时除了 drain 内存队列，
# 还增量读取 jsonl 尾部，保证任何进程发布的修改都能实时显示。

_TAIL_LOCK = threading.Lock()


def read_history_tail(cursor: int = 0, max_bytes: int = 0):
    """增量读取历史文件尾部新增事件（线程安全，跨进程兜底）。

    Args:
        cursor: 上次读取到的字节偏移（0 = 从头读取）。
        max_bytes: 单次最多读取字节数（0 = 不限制）。
            限制后返回的 cursor = min(文件大小, cursor + 读取字节)，
            未读完的部分下次轮询继续（每轮 UI 线程工作量有上限，防卡死）。

    Returns:
        (recs, new_cursor):
            recs       解析出的新事件列表（可能为空）
            new_cursor 本次读取后的文件字节偏移（下一次的 cursor）
        若文件被修剪/变小（小于 cursor），返回 (None, 文件大小)，
        调用方应重置游标后重新读取（合并时靠 seq 去重，不会重复）。
    """
    if not _HISTORY_PATH.exists():
        return [], 0
    try:
        size = _HISTORY_PATH.stat().st_size
        if cursor > size:
            # 文件被修剪过（超过 300 条/5MB 会删头部）→ 通知重置
            return None, size
        with _TAIL_LOCK:
            with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
                if cursor > 0:
                    f.seek(cursor)
                data = f.read(max_bytes) if max_bytes and max_bytes > 0 else f.read()
        recs = []
        for ln in data.splitlines():
            if not ln.strip():
                continue
            try:
                recs.append(json.loads(ln))
            except Exception:
                # 游标落在半行处（文件被并发追加/裁剪）→ 跳过该行碎片，
                # 下一轮从新游标续读可恢复完整行，不丢事件
                continue
        if max_bytes and max_bytes > 0:
            # 限流读时：若截断落在半行处，游标回退到最后一个完整换行之后，
            # 下轮从完整行开头重读，保证不丢记录（单条记录 ≤120KB < 512KB 上限，
            # 不会出现整块无换行的死循环）
            last_nl = data.rfind("\n")
            if last_nl < 0:
                new_cursor = cursor          # 整块无换行：下轮重读同一块
            elif last_nl < len(data) - 1:
                new_cursor = cursor + last_nl + 1   # 回退到半行之前
            else:
                new_cursor = cursor + len(data)     # 恰好整行结束
            new_cursor = min(new_cursor, size)
        else:
            new_cursor = size
        return recs, new_cursor
    except Exception:
        return [], cursor


def history_tail_size() -> int:
    """当前历史文件字节大小（用于初始化游标）"""
    try:
        return _HISTORY_PATH.stat().st_size
    except Exception:
        return 0
