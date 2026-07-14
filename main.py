#!/usr/bin/env python3
"""
7坛AI小编 — 主入口
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

# 修复 Windows 控制台 GBK 编码问题（emoji 字符无法编码）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(PROJECT_ROOT / ".env")


def setup_logging():
    """配置日志"""
    from src.utils.logger import setup_logging
    setup_logging()


def main():
    """主入口 — 委托给 cli.py 处理参数"""
    from src.cli import parse_args

    args = parse_args()

    # 配置日志
    log_level = getattr(args, 'log_level', 'INFO')
    setup_logging()

    # 确保已初始化（GUI 模式下静默生成默认配置，不弹 CLI 引导）
    from src.config.loader import ensure_initialized
    mode = args.command
    ensure_initialized(interactive=(mode not in ("desktop", "scheduler")))

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
    import threading
    from src.scheduler.scheduler import start_scheduler
    from src.config.loader import load_config

    config = load_config()
    start_scheduler(config)

    host = "127.0.0.1"
    port = getattr(args, 'port', 9800)

    # 后台启动 FastAPI 服务器
    def _run_server():
        from src.web.server import start_server
        start_server(host=host, port=port)

    threading.Thread(target=_run_server, daemon=True).start()

    # ===== 等待后端就绪，再启动 GUI =====
    import time as _time
    import requests as _requests
    logger.info("⏳ 等待后端服务就绪...")
    for _i in range(30):  # 最多等 15 秒
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
        import time as _time
        _time.sleep(300)


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

    logger.info("⏰ 调度器已启动，按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("👋 调度器已停止")


def run_cli(args):
    """交互式 CLI"""
    from src.agent.agent_loop import run_agent_loop
    from src.agent.conversation import create_session

    print("\n" + "=" * 50)
    print("  🤖 7坛AI小编 — 交互式 CLI")
    print("  输入任务指令，AI 将自动执行")
    print("  输入 /help 查看更多命令")
    print("=" * 50 + "\n")

    session_id = create_session()
    model = getattr(args, 'model', None)

    while True:
        try:
            user_input = input("👉 ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见!")
            break

        if not user_input:
            continue

        # 特殊命令
        if user_input.startswith("/"):
            cmd = user_input[1:].lower()
            if cmd == "help":
                print("""
命令列表:
  /help      - 显示帮助
  /quit      - 退出
  /status    - 系统状态
  /costs     - 费用报告
  /new       - 新对话
  /resources - 查看资源列表
  /jobs      - 查看定时任务
  /web       - 启动 Web 界面
                """)
            elif cmd == "quit" or cmd == "exit":
                print("👋 再见!")
                break
            elif cmd == "status":
                from src.tools.monitor_tools import get_system_status
                print(get_system_status())
            elif cmd == "costs":
                from src.tools.monitor_tools import get_cost_report
                print(get_cost_report(days=7))
            elif cmd == "new":
                session_id = create_session()
                print(f"🆕 新对话: {session_id}")
            elif cmd == "resources":
                from src.database.db import get_session, Resource
                session = get_session()
                try:
                    resources = session.query(Resource).order_by(
                        Resource.created_at.desc()
                    ).limit(10).all()
                    for r in resources:
                        print(f"  [{r.status}] {r.title} ({r.resource_type})")
                    print(f"  共 {len(resources)} 条记录")
                finally:
                    session.close()
            elif cmd == "jobs":
                from src.scheduler.scheduler import get_jobs_status
                jobs = get_jobs_status()
                for j in jobs:
                    print(f"  {j['name']}: 下次 {j['next_run'] or '-'}")
            elif cmd == "web":
                print("启动 Web 界面...")
                run_web(args)
                break
            else:
                print(f"未知命令: /{cmd}. 输入 /help 查看帮助")
        else:
            print("⏳ 执行中...")
            result = run_agent_loop(task=user_input, session_id=session_id, model_name=model)
            print(f"\n{'✅ 成功' if result['success'] else '❌ 失败'} (¥{result.get('cost', 0):.4f})")
            print(result.get("result", ""))
            print()


if __name__ == "__main__":
    main()
