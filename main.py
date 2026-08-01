#!/usr/bin/env python3
"""
7Tan — 主入口
绿色免安装 AI 编辑器，自动抓取→改写→发布游戏/软件资源

用法:
    python main.py                  # 启动桌面应用
    python main.py run "任务描述"    # 执行单次任务
    python main.py setup            # 重新运行初始化向导
"""
import sys
import os
from pathlib import Path


def _get_project_root():
    """获取项目根目录 — 兼容开发模式和 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


# 确保项目根目录在 path 中
PROJECT_ROOT = _get_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

# 🔧 全局修复: subprocess text=True 在 Windows 中文系统下默认用 GBK 解码，
# 遇到 UTF-8 内容会 UnicodeDecodeError。这里在入口统一补丁为 utf-8。
import subprocess as _subprocess

_original_run = _subprocess.run
_original_popen = _subprocess.Popen

def _patched_run(*args, **kwargs):
    if kwargs.get('text') and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
        kwargs['errors'] = 'replace'
    if sys.platform == 'win32':
        existing = kwargs.get('creationflags', 0)
        kwargs['creationflags'] = existing | _subprocess.CREATE_NO_WINDOW
    return _original_run(*args, **kwargs)

class _PatchedPopen(_subprocess.Popen):
    def __init__(self, *args, **kwargs):
        if kwargs.get('text') and 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
            kwargs['errors'] = 'replace'
        if sys.platform == 'win32':
            existing = kwargs.get('creationflags', 0)
            kwargs['creationflags'] = existing | _subprocess.CREATE_NO_WINDOW
        super().__init__(*args, **kwargs)

_subprocess.run = _patched_run
_subprocess.Popen = _PatchedPopen

# 修复 Windows 控制台 GBK 编码问题（emoji 字符无法编码）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ⚡ 尽早导入 console_panel，触发 OS 级管道重定向（必须在 loguru 之前）
# ⚠️ 部分环境下 install_all() 中的 dup2 可能阻塞，容错跳过
try:
    import src.ui.console_panel as _console_panel  # noqa: F401
except Exception:
    pass

# 🔍 崩溃诊断 — 捕获未处理异常和 segfault
import traceback as _tb
_CRASH_DIR = PROJECT_ROOT / "logs"
_CRASH_DIR.mkdir(parents=True, exist_ok=True)

def _crash_handler(exc_type, exc_value, exc_tb):
    """捕获所有未处理的 Python 异常"""
    crash_path = _CRASH_DIR / f"crash_{os.getpid()}.txt"
    with open(crash_path, "w", encoding="utf-8") as f:
        f.write(f"CRASH PID={os.getpid()}\n{exc_type.__name__}: {exc_value}\n\n")
        _tb.print_exception(exc_type, exc_value, exc_tb, file=f)
    sys.__excepthook__(exc_type, exc_value, exc_tb)
sys.excepthook = _crash_handler

import faulthandler
_segfault_log = None
try:
    _segfault_log = open(_CRASH_DIR / f"segfault_{os.getpid()}.txt", "w", buffering=1)
    faulthandler.enable(file=_segfault_log, all_threads=True)
except Exception:
    faulthandler.enable(file=sys.stderr, all_threads=True)

from loguru import logger
from dotenv import load_dotenv

# ===== Phase 2: 启动安全防护 =====
import ctypes as _ctypes
from src.security.safe_modify import restore_latest_backup, restore_all_from_backup

# 加载环境变量
load_dotenv(PROJECT_ROOT / ".env")


def setup_logging():
    """配置日志"""
    import logging
    # 屏蔽 httpx/httpcore 的 INFO 日志（OpenAI SDK 底层HTTP请求日志太啰嗦）
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    from src.utils.logger import setup_logging as _setup
    _setup()
    # logger.remove() 会清除所有 sink，需要重新注册控制台 sink
    import src.ui.console_panel as _cp
    _cp.refresh_loguru_sink()


def main():
    """主入口 — 委托给 cli.py 处理参数"""
    from src.cli import parse_args

    args = parse_args()

    # 配置日志
    log_level = getattr(args, 'log_level', 'INFO')
    setup_logging()

    # 确保已初始化（GUI 模式下静默生成默认配置，不弹 CLI 引导）
    from src.config.loader import ensure_initialized
    ensure_initialized(interactive=(args.command not in ("desktop", "scheduler")))

    # 🔄 清理残留的重启锁（上次异常退出可能残留 .restart_lock，阻塞后续重启）
    try:
        from src.scheduler.daemon import cleanup_stale_restart_locks
        cleanup_stale_restart_locks()
    except Exception:
        pass

    # 初始化数据库
    from src.database.db import init_db
    init_db()

    # 路由到对应模式
    mode = args.command
    if mode == "desktop":
        run_desktop(args)
    elif mode == "run":
        run_task(args)
    elif mode == "setup":
        run_setup()
    elif mode == "integrity":
        run_integrity()
    elif mode == "scheduler":
        run_scheduler()
    else:
        run_cli(args)


def is_safe_mode():
    """
    检测是否进入安全模式。
    触发方式：按住 Shift 启动 或 命令行 --safe-mode
    """
    if "--safe-mode" in sys.argv:
        return True
    try:
        return bool(_ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000)
    except Exception:
        return False


def startup_self_check():
    """
    启动自检。
    检查关键 .pyd 存在、核心模块导入、main.py 语法完整性。

    Returns:
        (ok: bool, msg: str)
    """
    required_pyd = [
        "src/security/license_verify.pyd",
        "src/security/rsa_verify.pyd",
        "src/security/safe_modify.pyd",
    ]

    # ① 检查关键 .pyd 文件存在（未编译时用 .py 回退）
    # PyInstaller 打包后模块在 exe 内部，文件系统中不存在，跳过文件检查
    if not getattr(sys, 'frozen', False):
        for f in required_pyd:
            py_path = PROJECT_ROOT / f
            py_fallback = PROJECT_ROOT / f.replace(".pyd", ".py")
            if not py_path.exists() and not py_fallback.exists():
                return False, f"核心文件缺失: {f}"

    # ② 尝试导入关键模块
    try:
        from src.security.license_verify import verify_license  # noqa: F401
        from src.security.safe_modify import pre_modify_check  # noqa: F401
    except ImportError as e:
        return False, f"核心模块导入失败: {e}"

    # ③ 检查 main.py 语法完整性（PyInstaller 打包后 __file__ 指向 exe 而非 .py，跳过）
    try:
        if not getattr(sys, 'frozen', False):
            with open(__file__, "r", encoding="utf-8") as f:
                compile(f.read(), __file__, "exec")
    except SyntaxError as e:
        return False, f"main.py 语法错误: {e}"

    return True, "OK"


def attempt_recovery():
    """
    尝试从备份恢复。

    Returns:
        成功恢复的文件列表（空列表=恢复失败或无备份）
    """
    try:
        restored = restore_latest_backup()
        if restored:
            logger.info(f"🔄 已回滚 {len(restored)} 个文件: {restored}")
        return restored
    except Exception as e:
        logger.error(f"回滚失败: {e}")
        return []


def run_desktop(args):
    """启动原生桌面应用 — PyQt6 全原生控件，后端异步初始化"""
    # 沙盒模式：由 sandbox_execute 的子进程设置，防止意外启动 GUI
    if os.environ.get("SANDBOX_MODE") == "1":
        return

    # ===== 清理残留重启锁 =====
    try:
        from src.scheduler.daemon import cleanup_stale_restart_locks
        cleanup_stale_restart_locks()
    except Exception:
        pass

    # ===== 遥测上报（专业版水印回传，静默不阻塞）=====
    try:
        from src.core.telemetry import report_async
        report_async()
    except Exception:
        pass

    # ===== 安全模式处理 =====
    if is_safe_mode():
        logger.warning("🛟 检测到安全模式启动信号")
        restored = restore_all_from_backup()
        if restored:
            logger.info(f"🛟 安全模式: 已恢复 {len(restored)} 个文件到原始版本")
            # 弹窗告知（用 tkinter，避免依赖任何可能损坏的模块）
            try:
                import tkinter.messagebox as _mb
                _mb.showinfo(
                    "7Tan - 安全模式",
                    f"已进入安全模式。\n\n"
                    f"所有用户修改已回滚到原始版本（{len(restored)} 个文件）。\n"
                    "你可以重新开始修改。"
                )
            except Exception:
                pass
        else:
            logger.warning("🛟 安全模式: 无备份可恢复")

    # ===== 启动自检 =====
    ok, msg = startup_self_check()
    if not ok:
        logger.error(f"❌ 启动自检失败: {msg}")
        restored = attempt_recovery()
        if restored:
            try:
                import tkinter.messagebox as _mb
                _mb.showwarning(
                    "7Tan - 自动修复",
                    f"检测到以下文件修改导致启动失败：\n{msg}\n\n"
                    f"已自动回滚 {len(restored)} 个文件。\n"
                    "点击确定后重新启动。"
                )
            except Exception:
                pass
            # 重启（启动恢复场景，调度器/浏览器/DB 尚未初始化，无需清理）
            import subprocess as _sp
            if sys.platform == "win32":
                _sp.Popen(
                    [sys.executable] + sys.argv,
                    creationflags=_sp.CREATE_NEW_PROCESS_GROUP | _sp.DETACHED_PROCESS,
                    stdin=_sp.DEVNULL,
                    stdout=_sp.DEVNULL,
                    stderr=_sp.DEVNULL,
                    close_fds=True,
                )
            else:
                _sp.Popen(
                    [sys.executable] + sys.argv,
                    start_new_session=True,
                    stdin=_sp.DEVNULL,
                    stdout=_sp.DEVNULL,
                    stderr=_sp.DEVNULL,
                    close_fds=True,
                )
            sys.exit(0)
        else:
            try:
                import tkinter.messagebox as _mb
                _mb.showerror(
                    "7Tan - 启动失败",
                    f"启动失败且无法自动修复：\n{msg}\n\n"
                    "请尝试：\n"
                    "1. 按住 Shift 双击启动 → 安全模式\n"
                    "2. 重新安装软件"
                )
            except Exception:
                pass
            sys.exit(1)
    else:
        logger.info("✅ 启动自检通过")

    import threading
    from src.scheduler.scheduler import start_scheduler
    from src.config.loader import load_config

    config = load_config()
    start_scheduler(config)

    host = "127.0.0.1"
    port = getattr(args, 'port', 9800)

    # 后台启动 FastAPI 服务器
    def _run_server():
        try:
            from src.web.server import start_server
            start_server(host=host, port=port)
        except Exception as e:
            logger.exception(f"❌ 后端服务启动失败: {e}")

    threading.Thread(target=_run_server, daemon=True).start()

    # ===== 等待后端就绪，再启动 GUI =====
    import time as _time
    import requests as _requests
    logger.info("⏳ 等待后端服务就绪...")
    for _i in range(60):  # 最多等 30 秒
        try:
            resp = _requests.get(f"http://{host}:{port}/api/health", timeout=2)
            if resp.status_code == 200:
                logger.info("✅ 后端服务已就绪")
                break
        except Exception:
            pass
        _time.sleep(0.5)
    else:
        logger.warning("⚠️ 后端服务启动超时，GUI 仍将启动")

    # ===== GUI 启动 =====
    logger.info("🚀 正在启动 PyQt6 桌面应用...")

    # 加载已安装的插件
    try:
        from src.plugins import get_manager
        mgr = get_manager()
        mgr.load_all_installed()
        logger.info("📦 插件已加载")
    except Exception as e:
        logger.warning(f"插件加载跳过: {e}")

    try:
        from src.ui.app import launch_app
        launch_app()
    except Exception as e:
        logger.exception(f"❌ PyQt6 启动失败: {e}")
        print(f"\n❌ GUI 启动失败: {e}")
        print("按 Enter 退出...")
        input()


def run_task(args):
    """执行单次任务"""
    task_text = " ".join(getattr(args, 'task', []))
    if not task_text.strip():
        logger.error("任务描述不能为空")
        return

    from src.pipeline.pipeline import Pipeline
    pipeline = Pipeline()
    result = pipeline.run(task=task_text, model=getattr(args, 'model', None))

    print("\n" + "=" * 50)
    print(f"{'✅ 任务完成' if result['success'] else '❌ 任务失败'}")
    print(f"费用: ¥{result.get('cost', 0):.4f}")
    print(f"迭代: {result.get('iterations', 0)} 次")
    print("-" * 50)
    print(result.get("result", ""))
    print("=" * 50)


def run_setup():
    """重新运行初始化向导"""
    from src.config.loader import cli_first_time_setup
    cli_first_time_setup()


def run_integrity():
    """完整性检查"""
    from src.security.integrity import IntegrityChecker
    checker = IntegrityChecker()
    ok = checker.check_all()
    report = checker._report
    if report:
        print(report)
    print(f"{'✅ 完整性检查通过' if ok else '❌ 完整性检查未通过'}")


def run_scheduler():
    """仅运行调度器（无 Web 界面）"""
    from src.scheduler.scheduler import start_scheduler
    from src.config.loader import load_config
    import time

    config = load_config()
    start_scheduler(config)

    logger.info("📅 调度器已启动，Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 调度器已停止")


def run_cli(args):
    """交互式命令行"""
    from src.agent.agent_loop import run_agent_loop
    run_agent_loop()


if __name__ == "__main__":
    main()
