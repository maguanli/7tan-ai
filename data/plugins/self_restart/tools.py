"""
自我重启插件 — 让 AI 能够自动重启自己
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
    # 尝试多个位置
    candidates = [
        ROOT / "dist" / "7tan-editor" / "7tan-editor.exe",
        ROOT / "7tan-editor.exe",
        Path(sys.executable) if sys.executable.endswith(".exe") else None,
    ]
    for c in candidates:
        if c and c.exists():
            return c
    # 最后 fallback
    return ROOT / "dist" / "7tan-editor" / "7tan-editor.exe"


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
    
    # 写一个 watchdog 批处理
    bat_path = exe_path.parent / "restart_watchdog.bat"
    bat_content = f'''@echo off
timeout /t {delay_seconds} /nobreak >nul
start "" "{exe_path}"
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
        
        # 立即退出当前进程
        os._exit(0)
    except Exception as e:
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
    import sys
    info = []
    info.append(f"Python: {sys.executable}")
    info.append(f"Version: {sys.version}")
    info.append(f"PATH Python: {os.environ.get('PATH', '')[:200]}")
    
    # 查找 sandbox_execute 的实现
    sandbox_files = list(ROOT.rglob("*sandbox*"))
    info.append(f"Sandbox相关文件: {[str(f.relative_to(ROOT)) for f in sandbox_files]}")
    
    return "\n".join(info)
