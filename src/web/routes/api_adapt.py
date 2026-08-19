# -*- coding: utf-8 -*-
"""
平台适配 API — 其他系统包 WEB 版「插件复制适配」向导

GET  /api/adapt/check   — 体检：当前系统 + 全部插件兼容性（只读，快）
POST /api/adapt/run     — 执行适配（后台进程，用户确认后一口气完成）
GET  /api/adapt/status  — 适配状态/进度（WEB 前端轮询）
GET  /api/adapt/report  — 最近一次适配报告
GET  /api/adapt/log     — 适配过程日志（尾部，供前端展示）

说明：
    适配过程可能包含 pip 安装依赖（几十秒~几分钟），因此在子进程中后台执行，
    前端通过 /status + /log 轮询进度；适配完成会写入 adapt_report.json / adapt_status.json。
"""
from fastapi import APIRouter, Query
import json
import os
import sys
import subprocess
from pathlib import Path

router = APIRouter(prefix="/api/adapt", tags=["adapt"])

ROOT = Path(__file__).resolve().parent.parent.parent.parent
ADAPTER = ROOT / "tools" / "platform_adapter.py"
LOCK_FILE = ROOT / "data" / "adapt_running.lock"
LOG_FILE = ROOT / "data" / "adapt_run.log"
REPORT_FILE = ROOT / "data" / "plugins" / "adapt_report.json"
STATUS_FILE = ROOT / "data" / "plugins" / "adapt_status.json"


def _read_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _is_running() -> bool:
    """适配进程是否在运行（锁文件 + 进程存活检查）"""
    try:
        if not LOCK_FILE.exists():
            return False
        pid = int(LOCK_FILE.read_text(encoding="utf-8").strip() or "0")
        if pid <= 0:
            return False
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                               capture_output=True, text=True, timeout=10)
            return str(pid) in r.stdout
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    except Exception:
        return False


@router.get("/check")
async def check(platform: str = Query("", description="模拟平台（可选，如 darwin/linux）")):
    """体检：当前系统 + 各插件兼容性（只读）"""
    cmd = [sys.executable, str(ADAPTER), "--check", "--json"]
    if platform.strip():
        cmd += ["--platform", platform.strip().lower()]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, cwd=str(ROOT))
        out = (proc.stdout or "").strip()
        # platform_adapter --json 输出的是多行缩进 JSON；先整体解析，
        # 失败则截取第一个 { 到最后一个 }（兼容混入的日志行）
        try:
            return json.loads(out)
        except Exception:
            start = out.find("{")
            end = out.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(out[start:end + 1])
                except Exception:
                    pass
        return {"error": (proc.stderr or out)[-600:], "returncode": proc.returncode}
    except Exception as e:
        return {"error": f"体检失败: {e}"}


@router.post("/run")
async def run():
    """执行适配（用户确认后调用）：后台进程一口气完成复制+装依赖+自测+启用"""
    if _is_running():
        return {"ok": False, "msg": "适配已在运行中，请稍候"}
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
        log_f = open(LOG_FILE, "w", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(ADAPTER), "--adapt"],
            cwd=str(ROOT), stdout=log_f, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
        # 把真实适配子进程 PID 写入锁文件（替换 WEB 进程 PID）
        try:
            LOCK_FILE.write_text(str(proc.pid), encoding="utf-8")
        except Exception:
            pass
        return {"ok": True, "msg": "适配已启动", "pid": proc.pid}
    except Exception as e:
        return {"ok": False, "msg": f"启动适配失败: {e}"}


@router.get("/status")
async def status():
    """适配状态：running / done / error + 已保存的适配状态"""
    running = _is_running()
    report = _read_json(REPORT_FILE)
    status_data = _read_json(STATUS_FILE)
    log_tail = ""
    try:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            log_tail = "\n".join(lines[-30:])
    except Exception:
        pass
    return {
        "running": running,
        "has_report": bool(report),
        "report": report,
        "status": status_data,
        "log_tail": log_tail,
    }


@router.get("/report")
async def report():
    """最近一次适配报告"""
    return _read_json(REPORT_FILE, {"empty": True})


@router.get("/log")
async def log(tail: int = Query(100, ge=1, le=2000)):
    """适配过程日志（尾部 N 行）"""
    try:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            return {"lines": lines[-tail:]}
    except Exception:
        pass
    return {"lines": []}
