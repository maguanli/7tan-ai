"""
自我重启插件 — 让 AI 能够自动重启自己

修复记录 (2025-07-18):
  - P0-1: os._exit(0) → QApplication.quit() 优雅退出，3秒超时兜底
  - P0-2: 重启看门狗加单例锁，防止多实例风暴
"""
import sys
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


def _find_exe() -> Path:
    """找到 7tan-editor.exe 的路径"""
    candidates = [
        ROOT / "dist" / "7tan-editor" / "7tan-editor.exe",
        ROOT / "7tan-editor.exe",
        Path(sys.executable) if sys.executable.endswith(".exe") else None,
    ]
    for c in candidates:
        if c and c.exists():
            return c
    return ROOT / "dist" / "7tan-editor" / "7tan-editor.exe"


def _graceful_exit(delay_seconds: int = 2):
    """
    优雅退出：先尝试 QApplication.quit()，
    超时后 os._exit(0) 兜底（避免僵尸进程）
    """
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        app = QApplication.instance()
        if app is not None:
            # 兜底：3秒后还没退出就硬杀
            QTimer.singleShot(max(delay_seconds + 1, 3) * 1000, lambda: os._exit(0))
            app.quit()
            return
    except Exception:
        pass

    # 没有 Qt 实例或 Qt 不可用，直接退出
    os._exit(0)


@register_tool(
    name="self_restart",
    description="自动重启应用程序。AI 可以调用此工具来重启自己。重启后约3秒新窗口会自动打开。",
    parameters={
        "type": "object",
        "properties": {
            "delay_seconds": {
                "type": "integer",
                "description": "重启前等待秒数，默认2秒",
                "default": 2,
            },
        },
        "required": [],
    },
    category="system",
)
def self_restart(delay_seconds: int = 2) -> str:
    """重启应用程序"""
    exe_path = _find_exe()

    if not exe_path.exists():
        return f"❌ 找不到可执行文件: {exe_path}"

    # ── P0-2: 单例锁 — 防止多个看门狗同时运行 ──
    lock_file = exe_path.parent / ".restart_lock"

    if lock_file.exists():
        try:
            old_pid = int(lock_file.read_text().strip())
            # 检查旧 PID 是否还活着
            os.kill(old_pid, 0)
            return f"⚠️ 已有重启看门狗在运行 (PID={old_pid})，跳过本次重启"
        except (ValueError, OSError):
            # 旧锁已过期，清理
            try:
                lock_file.unlink()
            except Exception:
                pass

    # 写入当前 PID 作为锁
    lock_file.write_text(str(os.getpid()))

    # ── 写 watchdog 批处理 ──
    bat_path = exe_path.parent / "restart_watchdog.bat"
    bat_content = f'''@echo off
timeout /t {delay_seconds} /nobreak >nul
start "" "{exe_path}"
REM 等新进程启动后再删锁
timeout /t 3 /nobreak >nul
del "{lock_file}" 2>nul
del "%~f0" 2>nul
'''
    bat_path.write_text(bat_content, encoding="gbk")

    try:
        # 用完全脱离的方式启动 watchdog
        subprocess.Popen(
            ["cmd", "/c", str(bat_path)],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

        # ── P0-1: 优雅退出，而不是 os._exit(0) 直接暴毙 ──
        _graceful_exit(delay_seconds)
    except Exception as e:
        # 失败了清理锁文件
        try:
            lock_file.unlink()
        except Exception:
            pass
        return f"❌ 重启失败: {e}"

    return "🔄 正在重启..."


@register_tool(
    name="self_fix_sandbox",
    description="诊断并修复 sandbox_execute 工具的问题。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="system",
)
def self_fix_sandbox() -> str:
    """修复 sandbox_execute"""
    info = []
    info.append(f"Python: {sys.executable}")
    info.append(f"Version: {sys.version}")
    info.append(f"PATH Python: {os.environ.get('PATH', '')[:200]}")

    sandbox_files = list(ROOT.rglob("*sandbox*"))
    info.append(f"Sandbox相关文件: {[str(f.relative_to(ROOT)) for f in sandbox_files]}")

    return "\n".join(info)
