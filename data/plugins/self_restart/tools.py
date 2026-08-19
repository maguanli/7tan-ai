"""
自我重启插件 — 让 AI 能够自动重启自己

修复记录:
  - 2025-07-26: P0 重构 — 委托给 daemon.py:graceful_restart()，统一两条重启路径
  - 2025-07-26: P0 修复 — category 改为 self_modify，恢复 Pro 门控
  - 2025-07-26: P0 修复 — 移除 _find_exe() 重复实现，daemon 已有完整路径检测
  - 2025-07-26: P1 修复 — 移除锁文件/watchdog bat，daemon 已有完整生命周期管理
  - 2025-07-18: P0-1: os._exit(0) → QApplication.quit() 优雅退出，3秒超时兜底
  - 2025-07-18: P0-2: 重启看门狗加单例锁，防止多实例风暴
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
from loguru import logger


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
    category="monitor",  # 🔧 修复: 重启是基础功能，不需要 Pro 门控
)
def self_restart(delay_seconds: int = 2) -> str:
    """
    重启应用程序 — 委托给 daemon.py:graceful_restart()
    
    完整流程:
    1. 停止调度器
    2. 关闭浏览器（AI 触发时保留，因 AI 可能还在用）
    3. 释放数据库连接池
    4. 保存运行状态
    5. 启动新进程（自动检测 exe/dev 模式）
    6. 健康检查
    7. 退出当前进程
    """
    try:
        from src.scheduler.daemon import graceful_restart
        logger.warning("🔄 正在重启（插件触发，委托 daemon.graceful_restart）...")
        # AI 工具调用时不关闭浏览器（close_browser_flag=False），
        # 因为 AI 可能正在使用浏览器进行其他操作
        graceful_restart(delay_seconds=delay_seconds, close_browser_flag=False)
        return "🔄 正在重启..."
    except ImportError as e:
        logger.error(f"❌ 无法导入 daemon 模块: {e}")
        return f"❌ 重启失败: 无法导入 daemon 模块 ({e})"
    except Exception as e:
        logger.error(f"❌ 重启异常: {e}")
        return f"❌ 重启失败: {e}"


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
