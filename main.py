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
def _patched_run(*args, **kwargs):
    if kwargs.get('text') and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
        kwargs['errors'] = 'replace'
    return _original_run(*args, **kwargs)
_subprocess.run = _patched_run

# 修复 Windows 控制台 GBK 编码问题（emoji 字符无法编码）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# 🔍 调试日志：stderr 双写 + faulthandler（排查闪退用，不影响正常启动）
import datetime as _dt
_CRASH_LOG = PROJECT_ROOT / "logs" / f"debug_stderr_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
_CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
class _TeeStderr:
    def __init__(self, primary, crash_file):
        self.primary = primary
        self.crash = open(crash_file, 'w', encoding='utf-8', buffering=1)
    def write(self, data):
        self.primary.write(data)
        self.crash.write(data)
        self.crash.flush()
    def flush(self):
        self.primary.flush()
        self.crash.flush()
sys.stderr = _TeeStderr(sys.stderr, _CRASH_LOG)

# 🔍 faulthandler 捕获 segfault
import faulthandler
_fh_log = PROJECT_ROOT / "logs" / f"debug_faulthandler_{os.getpid()}.txt"
_fh_log.parent.mkdir(parents=True, exist_ok=True)
faulthandler.enable(file=open(_fh_log, 'w', encoding='utf-8'))

# ⚡ 尽早导入 console_panel，触发 OS 级管道重定向（必须在 loguru 之前）
# 原理：os.pipe() + os.dup2() 在 OS 层面重定向 fd 1/2，
# 之后所有输出（print、loguru、C扩展、子进程）都会被管道捕获，
# 在 GUI 实时控制台中显示，和黑窗完全一致。
import src.ui.console_panel as _console_panel  # noqa: F401

from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(PROJECT_ROOT / ".env")


def setup_logging():
    """配置日志"""
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


def run_desktop(args):
    """启动原生桌面应用 — PyQt6 全原生控件，后端异步初始化"""
    # 沙盒模式：由 sandbox_execute 的子进程设置，防止意外启动 GUI
    if os.environ.get("SANDBOX_MODE") == "1":
        return

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
