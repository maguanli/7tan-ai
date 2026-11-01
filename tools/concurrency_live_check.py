# -*- coding: utf-8 -*-
"""并发实测工具 —— 用「外部可核对的证据」验证多任务是否真并行。

为什么这么做：
    脚本自己打印「我并发了」不算证据。这里让每个任务把
    (pid, 祖先进程链, t_start, t_end) 写进 JSONL，
    再看时间区间是否两两重叠、祖先进程是否为应用主进程。

用法（两种模式）：
    # 1) 任务模式：由 Agent 在同一轮里发起 4 个并行调用
    python tools/concurrency_live_check.py task T1 5

    # 2) 报告模式：读回记录，判断是否真并发、由谁派发
    python tools/concurrency_live_check.py report [--reset]

判定标准：
    · 两两时间区间重叠        → 真并行（不是快速轮转）
    · 祖先进程链包含应用 PID → 由应用主进程派发，而不是别的进程
    · 墙钟 ≈ 单个任务耗时     → 加速比接近任务数
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "logs", "concurrency_live.jsonl")
LOCK = os.path.join(ROOT, "data", "logs", "concurrency_live.lock")


def _ancestors(start_pid: int, depth: int = 4) -> list:
    """向上追溯进程链 [(pid, name), ...]。

    wmic 的 CSV 列顺序是 Node,Name,ParentProcessId —— 共 3 列。
    （第一版要求 4 列，导致链路恒为空，是个真 bug。）
    """
    chain = []
    cur = start_pid
    for _ in range(depth):
        try:
            out = subprocess.run(
                ["wmic", "process", "where", "ProcessId=%d" % cur,
                 "get", "ParentProcessId,Name", "/format:csv"],
                capture_output=True, text=True, errors="ignore", timeout=10,
            ).stdout.strip().splitlines()
        except Exception:
            break
        if len(out) < 2:
            break
        parts = [x.strip() for x in out[-1].split(",")]
        if len(parts) < 3:
            break
        name = parts[1]
        try:
            ppid = int(parts[2])
        except ValueError:
            break
        chain.append([cur, name])
        cur = ppid
        if cur <= 4:
            break
    return chain


def _cmdline(pid: int) -> str:
    """取命令行（用 /value 格式，避免 CommandLine 里的逗号破坏 CSV 解析）。"""
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "ProcessId=%d" % pid,
             "get", "CommandLine", "/value"],
            capture_output=True, text=True, errors="ignore", timeout=10,
        ).stdout
    except Exception:
        return ""
    for ln in out.splitlines():
        ln = ln.strip()
        if ln.startswith("CommandLine="):
            return ln[len("CommandLine="):].strip()
    return ""


def _append(rec: dict) -> None:
    """跨进程安全地追加一行（msvcrt 文件锁）。"""
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    try:
        import msvcrt
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(LOCK, "a") as lk:
            msvcrt.locking(lk.fileno(), msvcrt.LK_LOCK, 1)
            try:
                with open(OUT, "a", encoding="utf-8") as f:
                    f.write(line)
            finally:
                try:
                    msvcrt.locking(lk.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
    except Exception:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(line)


def cmd_task(argv) -> int:
    label = argv[0] if argv else "t0"
    dur = float(argv[1]) if len(argv) > 1 else 3.0

    t0 = time.time()
    time.sleep(dur)
    t1 = time.time()

    rec = {
        "task": label,
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "ancestors": _ancestors(os.getpid(), 4),
        "t_start": round(t0, 4),
        "t_end": round(t1, 4),
        "dur": round(t1 - t0, 3),
        "iso_start": datetime.fromtimestamp(t0).strftime("%H:%M:%S.%f")[:-3],
        "iso_end": datetime.fromtimestamp(t1).strftime("%H:%M:%S.%f")[:-3],
    }
    _append(rec)
    print("[%s] pid=%s %s -> %s (%.3fs)" % (
        label, rec["pid"], rec["iso_start"], rec["iso_end"], rec["dur"]))
    return 0


def cmd_report(argv) -> int:
    if "--reset" in argv and os.path.exists(OUT):
        os.remove(OUT)
        print("已清空 %s\n" % OUT)
        return 0

    if not os.path.exists(OUT):
        print("没有记录，先跑: python tools/concurrency_live_check.py task T1 5")
        return 1

    rows = []
    for line in io.open(OUT, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not rows:
        print("记录为空")
        return 1

    # 应用主进程：命令行含 main.py 的那个 pythonw.exe
    # （只看进程名会误选 venv 启动器 8640，真正跑 main.py 的是它的子进程）
    app_pid = None
    app_cmd = ""
    # 从子往父找：第一个命令行含 main.py 的 python 进程才是真正的工作进程。
    # 反方向会选中 .venv\Scripts\pythonw.exe 这个转发壳（它也带 main.py 参数）。
    for pid, name in (rows[0].get("ancestors") or []):
        if "python" not in (name or "").lower():
            continue
        cl = _cmdline(pid)
        if "main.py" in cl:
            app_pid, app_cmd = pid, cl
            break
    if app_pid is None:
        for pid, name in reversed(rows[0].get("ancestors") or []):
            if "pythonw" in (name or "").lower():
                app_pid = pid
                break

    print("进程链（以 %s 为例）:" % rows[0]["task"])
    if app_cmd:
        print("  应用主进程命令行: %s" % app_cmd[:100])
    for pid, name in rows[0].get("ancestors") or []:
        mark = "  <== 应用主进程" if pid == app_pid else ""
        print("  pid=%-6s %s%s" % (pid, name, mark))

    print()
    print("%-4s %-7s %-7s %-6s %-14s %-14s" % (
        "task", "pid", "ppid", "app", "start", "end"))
    all_hit = True
    for r in rows:
        chain_pids = [c[0] for c in (r.get("ancestors") or [])]
        hit = app_pid is not None and app_pid in chain_pids
        all_hit = all_hit and hit
        print("%-4s %-7s %-7s %-6s %-14s %-14s" % (
            r["task"], r["pid"], r.get("ppid"), "YES" if hit else "NO",
            r["iso_start"], r["iso_end"]))

    t0 = min(x["t_start"] for x in rows)
    t1 = max(x["t_end"] for x in rows)
    serial = sum(x["dur"] for x in rows)
    overlap = all(
        not (a["t_end"] <= b["t_start"] or b["t_end"] <= a["t_start"])
        for i, a in enumerate(rows) for b in rows[i + 1:]
    )
    wall = t1 - t0

    print()
    print("任务数            %d" % len(rows))
    print("全部源于应用进程  %s" % all_hit)
    print("两两区间重叠      %s" % overlap)
    print("串行应为          %.3fs" % serial)
    print("实际墙钟          %.3fs" % wall)
    print("加速比            %.2fx" % (serial / wall if wall else 0))
    verdict = overlap and all_hit and wall < serial * 0.6
    print("结论              %s" % ("真并发执行" if verdict else "未达并发预期"))
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mode = sys.argv[1].lower()
    rest = sys.argv[2:]
    if mode == "task":
        return cmd_task(rest)
    if mode == "report":
        return cmd_report(rest)
    print("未知模式: %s（task / report）" % mode)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
