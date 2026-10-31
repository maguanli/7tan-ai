# -*- coding: utf-8 -*-
"""命令执行作用域 与 全量审计 —— 无人值守 Worker 的两道围栏。

背景（2026-11-01）：
    agent_spawner 把 run_command 下放给了 Worker。run_command 能执行任意 shell，
    等于把完整系统权限交给一个没人看着的子 Agent。两条对应措施：

    ① 限定 cwd（本模块的 Scope）
       Worker 运行期间，压入一个「作用域帧」，帧里写明工作根目录。
       run_command 解析 cwd 时若落到根目录之外，直接拒绝执行，不降级、不放行。

    ② 全量审计（本模块的 audit / query）
       每条命令落盘到 data/logs/cmd_audit.jsonl：时间、作用域、cwd、命令原文、
       退出码、耗时、输出摘要、是否越界。事后可 query 检索。

设计要点（为什么用「帧栈」而不是全局变量）：
    spawn_worker 是在主 Agent 的线程里【同步】调用 run_agent_loop 的，
    也就是说主 Agent 和 Worker 共用同一个线程。若用全局变量或普通
    threading.local 单值，Worker 结束后无法恢复主 Agent 的宽松语义。
    参考 src/utils/abort_signal.py 的栈顶语义：
        主 Agent   无帧                      → 宽松（人在旁边）
        Worker 压帧 root=worktree, strict    → 严格
        Worker 弹帧                          → 恢复宽松
    跨线程时（P1 并发化，每个 Worker 独立线程）各线程的栈天然分离。

范围边界（必须说清，不能假装做到了）：
    · 本模块限制的是「命令从哪个目录启动」，不是「命令能碰哪些文件」。
      一条 `type C:\\Windows\\win.ini` 仍然能读到根目录之外的东西。
      所以额外做了 escape 检测：命令里出现的绝对路径若在作用域之外，
      记进审计的 outside 字段（strict_block_escape=True 时才拦截）。
    · 审计只覆盖「工具层执行的命令」（terminal_runner 的 _run_cmd 路径、
      run_shell_script 等）。主程序内部固定的 subprocess 调用
      （agent_loop 里的 git diff、m4_patch_system 里的验证脚本）
      不在此列 —— 那些命令是写死的，没有注入面。
"""
from __future__ import annotations

import contextvars
import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

__all__ = [
    "PROJECT_ROOT",
    "ScopeViolation",
    "Scope",
    "push",
    "pop",
    "current",
    "stack_info",
    "resolve_cwd",
    "detect_escape",
    "audit",
    "query",
    "audit_path",
]

# ── 路径 ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]      # src/utils/cmd_scope.py → 项目根
AUDIT_DIR = PROJECT_ROOT / "data" / "logs"
AUDIT_FILE = AUDIT_DIR / "cmd_audit.jsonl"
AUDIT_ROTATE_BYTES = 8 * 1024 * 1024                    # 8MB 轮转一次

_write_lock = threading.Lock()
_tls = threading.local()


class ScopeViolation(Exception):
    """cwd 落在作用域之外（严格模式下拒绝执行）。"""

    def __init__(self, message: str, target: str = "", root: str = ""):
        self.target = target
        self.root = root
        super().__init__(message)


class Scope:
    """一个作用域帧：谁在干活、它的工作根目录在哪、是否严格。"""

    __slots__ = ("root", "label", "strict", "block_escape", "hint", "pushed_at")

    def __init__(self, root, label="worker", strict=True, block_escape=False, hint=""):
        self.root = Path(root).resolve()
        self.label = str(label or "worker")
        self.strict = bool(strict)
        self.block_escape = bool(block_escape)
        self.hint = str(hint or "")
        self.pushed_at = time.time()

    def __repr__(self) -> str:
        return f"<Scope {self.label} root={self.root} strict={self.strict}>"


# ── 帧栈（ContextVar，跨线程池可传递）──────────────────────────
#
# 2026-11-01 修正：原来是 threading.local。实测发现 agent_optimizer 会把同一轮
# 里的多个工具丢进 ThreadPoolExecutor，池线程看不到 threading.local 的帧，
# 越界命令被放行（tools/probe_parallel_scope.py 复现：主线程拒绝 / 池线程放行）。
# 改为 ContextVar + tuple，配合 agent_optimizer 里的 copy_context().run()，
# 池线程拿到的就是提交那一刻的帧栈快照。
#
# 为什么存 tuple 而不是 list：ContextVar 存可变对象时，子上下文拿到的是同一个
# list 引用，子上下文里的 push 会污染父上下文。存不可变 tuple，每次 set 新值，
# 天然隔离。

_stack_var: contextvars.ContextVar = contextvars.ContextVar(
    "7tan_cmd_scope_stack", default=()
)


def _stack() -> list:
    return list(_stack_var.get())


def _set_stack(items) -> None:
    _stack_var.set(tuple(items))


def push(root, label="worker", strict=True, block_escape=False, hint="") -> Scope:
    """压入一个作用域帧，返回该帧（弹出时要传回来）。"""
    frame = Scope(root, label=label, strict=strict, block_escape=block_escape, hint=hint)
    s = _stack()
    s.append(frame)
    _set_stack(s)
    return frame


def pop(frame=None) -> None:
    """弹出作用域帧。传 frame 时按身份弹出（防止误弹别人的帧）。"""
    s = _stack()
    if not s:
        return
    if frame is None:
        s.pop()
        _set_stack(s)
        return
    for i in range(len(s) - 1, -1, -1):
        if s[i] is frame:
            del s[i]
            _set_stack(s)
            return


def current():
    """当前作用域帧；无帧返回 None（= 宽松语义：人在旁边看着）。"""
    s = _stack()
    return s[-1] if s else None


def stack_info() -> dict:
    """调试用：当前执行单元的帧栈概况。"""
    s = _stack()
    return {
        "thread": threading.get_ident(),
        "thread_name": threading.current_thread().name,
        "depth": len(s),
        "frames": [{"label": f.label, "root": str(f.root), "strict": f.strict} for f in s],
    }


# ── cwd 解析 ────────────────────────────────────────────────

def _is_inside(child: Path, parent: Path) -> bool:
    """child 是否在 parent 之内（含相等）。不同盘符返回 False。"""
    try:
        c = os.path.normcase(str(child))
        p = os.path.normcase(str(parent))
        if c == p:
            return True
        return os.path.commonpath([c, p]) == p
    except (ValueError, OSError):
        return False                 # 不同盘符 / 非法路径


def resolve_cwd(cwd, default_root=None) -> Path:
    """把工具传入的 cwd 解析成绝对路径，并按当前作用域校验。

    抛出 ScopeViolation：严格作用域下目标落在根目录之外。
    """
    scope = current()
    base = scope.root if scope else Path(default_root or PROJECT_ROOT)
    raw = (cwd or "").strip()

    if raw in ("", ".", "./", ".\\"):
        target = base
    else:
        p = Path(raw)
        target = p if p.is_absolute() else (base / p)

    try:
        target = target.resolve()
    except OSError as e:
        raise ScopeViolation(f"cwd 无法解析：{raw}（{e}）", target=str(raw),
                             root=str(base))

    if scope and scope.strict and not _is_inside(target, scope.root):
        raise ScopeViolation(
            f"cwd 越界：{target} 不在作用域根目录 {scope.root} 之内"
            f"（作用域：{scope.label}）",
            target=str(target), root=str(scope.root),
        )
    return target


# ── 命令内容里的越界线索 ────────────────────────────────────

_ABS_WIN = re.compile(r"[A-Za-z]:[\\/][^\s\"'|<>;,)]*")
_ABS_UNC = re.compile(r"\\\\[^\s\"'|<>;,)]+")
_CD_UP = re.compile(r"(?i)(?:^|[\s&|])(?:cd|chdir|pushd)\s+(?:/d\s+)?(\.\.[^\s&|]*)")


def detect_escape(command: str, root) -> dict:
    """扫描命令文本，找出可能跳出根目录的线索（只报告，不拦截）。"""
    cmd = command or ""
    root = Path(root).resolve()
    outside, inside = [], []

    for m in list(_ABS_WIN.finditer(cmd)) + list(_ABS_UNC.finditer(cmd)):
        token = m.group(0).rstrip("\\/")
        try:
            p = Path(token)
            p_abs = p if p.is_absolute() else None
        except Exception:
            continue
        if p_abs is None:
            continue
        if _is_inside(p_abs, root):
            inside.append(token)
        else:
            outside.append(token)

    ups = [m.group(1) for m in _CD_UP.finditer(cmd)]

    return {
        "outside_paths": outside[:8],
        "inside_paths": len(inside),
        "cd_up": ups[:4],
        "suspicious": bool(outside or ups),
    }


# ── 审计落盘 ────────────────────────────────────────────────

def _rotate_if_needed() -> None:
    try:
        if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size > AUDIT_ROTATE_BYTES:
            backup = AUDIT_FILE.with_suffix(".1.jsonl")
            try:
                if backup.exists():
                    backup.unlink()
            except OSError:
                pass
            AUDIT_FILE.replace(backup)
    except OSError:
        pass


def audit(tool: str, command: str, cwd=None, resolved_cwd=None,
          rc=None, duration_ms=None, stdout: str = "", stderr: str = "",
          timeout: int = None, aborted: bool = False, error: str = "",
          extra: dict = None) -> dict:
    """写一条审计记录。返回记录本身（便于调用方回显 / 测试断言）。

    审计写失败不阻断命令执行（否则磁盘满会导致所有命令不可用），
    但会把失败原因回显到调用方的返回值里——见 terminal_runner 的处理。
    """
    scope = current()
    ts = datetime.now()
    rec = {
        "ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": round(ts.timestamp(), 3),
        "tool": tool,
        "scope": scope.label if scope else "interactive",
        "scope_root": str(scope.root) if scope else str(PROJECT_ROOT),
        "strict": bool(scope.strict) if scope else False,
        "thread": threading.get_ident(),
        "cwd_in": str(cwd) if cwd is not None else "",
        "cwd": str(resolved_cwd) if resolved_cwd else "",
        "command": (command or "")[:4000],
        "rc": rc,
        "duration_ms": duration_ms,
        "timeout": timeout,
        "aborted": bool(aborted),
        "error": (error or "")[:500],
        "out_len": len(stdout or ""),
        "err_len": len(stderr or ""),
        "preview": (stdout or "").strip()[:600],
    }
    if scope:
        esc = detect_escape(command, scope.root)
        rec["outside"] = esc["outside_paths"]
        rec["escape"] = esc["suspicious"]
    if extra:
        rec.update(extra)

    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            _rotate_if_needed()
            with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        rec["_written"] = True
    except Exception as e:                              # noqa: BLE001
        rec["_written"] = False
        rec["_write_error"] = f"{type(e).__name__}: {e}"
    return rec


def _iter_records(limit_bytes: int = 4 * 1024 * 1024):
    """从审计文件尾部读取（最多 limit_bytes），逐行解析成 dict。"""
    if not AUDIT_FILE.exists():
        return []
    try:
        size = AUDIT_FILE.stat().st_size
        with open(AUDIT_FILE, "rb") as f:
            if size > limit_bytes:
                f.seek(size - limit_bytes)
                f.readline()                            # 丢掉半行
            raw = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []

    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def query(limit: int = 20, keyword: str = "", scope: str = "",
          only_failed: bool = False, only_escape: bool = False) -> list:
    """检索审计记录，返回最近 limit 条（时间倒序）。"""
    rows = _iter_records()
    kw = (keyword or "").strip().lower()
    sc = (scope or "").strip().lower()

    picked = []
    for r in rows:
        if kw and kw not in str(r.get("command", "")).lower() \
                and kw not in str(r.get("preview", "")).lower() \
                and kw not in str(r.get("tool", "")).lower():
            continue
        if sc and sc not in str(r.get("scope", "")).lower():
            continue
        if only_failed and r.get("rc") in (0, None) and not r.get("error"):
            continue
        if only_escape and not r.get("escape"):
            continue
        picked.append(r)

    picked.reverse()                                    # 最近的在前
    return picked[:max(1, int(limit or 20))]


def audit_path() -> Path:
    return AUDIT_FILE
