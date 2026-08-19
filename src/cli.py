"""
CLI 参数解析模块 — 统一命令行入口
支持: --desktop / --cli / --daemon / --headless / --port
"""
import argparse
import sys
from dataclasses import dataclass, field


@dataclass
class CliArgs:
    """命令行参数数据类"""
    command: str = "desktop"         # desktop / cli / run / setup / integrity / scheduler / web / web_autostart
    task: list = field(default_factory=list)
    model: str = None
    port: int = 9800
    daemon: bool = False            # 守护进程模式
    headless: bool = False          # 无头模式
    host: str = "0.0.0.0"          # API 服务绑定地址
    config: str = None              # 自定义配置文件路径
    log_level: str = "INFO"         # 日志级别
    web_autostart: str = None       # WEB 服务开机自启: install/uninstall/status/launch


def parse_args(args: list = None) -> CliArgs:
    """
    解析命令行参数

    用法:
        7tan-updater.exe                              # 默认桌面应用
        7tan-updater.exe --desktop                    # 启动桌面应用
        7tan-updater.exe --cli                        # 命令行对话
        7tan-updater.exe --daemon --headless          # 服务器后台
        7tan-updater.exe --desktop --port 8080        # 自定义端口
        7tan-updater.exe --run "爬取3DM游戏"           # 单次任务
        7tan-updater.exe --setup                      # 配置向导
        7tan-updater.exe --integrity                  # 完整性校验
    """

    parser = argparse.ArgumentParser(
        description="7Tan — 自动抓取→改写→发布",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  7tan-updater.exe                                # 桌面应用 (默认)
  7tan-updater.exe --desktop                      # 桌面应用模式
  7tan-updater.exe --cli                          # 命令行对话
  7tan-updater.exe --run "爬取3DM最新游戏"         # 执行单次任务
  7tan-updater.exe --setup                        # 重新初始化配置
  7tan-updater.exe --integrity                    # 生成/校验完整性
  7tan-updater.exe --scheduler                    # 仅运行调度器
  7tan-updater.exe --desktop --daemon --headless  # 服务器后台模式
  7tan-updater.exe --desktop --port 8080          # 自定义端口
        """,
    )

    # 运行模式 (互斥组)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--desktop", action="store_const", const="desktop", dest="command",
        help="启动桌面应用 (默认)",
    )
    mode.add_argument(
        "--cli", action="store_const", const="cli", dest="command",
        help="启动命令行对话模式",
    )
    mode.add_argument(
        "--run", type=str, nargs="?", const="", dest="run_task",
        help="执行单次任务 (如: --run '爬取游戏')",
    )
    mode.add_argument(
        "--setup", action="store_const", const="setup", dest="command",
        help="运行首次启动配置向导",
    )
    mode.add_argument(
        "--integrity", action="store_const", const="integrity", dest="command",
        help="生成/校验完整性文件",
    )
    mode.add_argument(
        "--scheduler", action="store_const", const="scheduler", dest="command",
        help="仅运行定时调度器（无 Web UI）",
    )
    mode.add_argument(
        "--web", action="store_const", const="web", dest="command",
        help="仅启动网页版控制面板服务（无桌面界面，关闭桌面版后仍可访问网页版）",
    )
    parser.add_argument(
        "--web-autostart",
        type=str,
        choices=["install", "uninstall", "status", "launch"],
        default=None,
        help="WEB 服务开机自启管理: install(配置自启)/uninstall(取消)/status(查看)/launch(启动服务)",
    )

    # 通用参数
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="指定 AI 模型名称",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=9800,
        help="API 服务器端口 (默认: 9800)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="API 服务器绑定地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        default=False,
        help="守护进程/后台服务模式",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="无头模式（服务器环境使用）",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="自定义配置文件路径",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )

    # 兼容旧式位置参数
    parser.add_argument(
        "legacy_command",
        nargs="?",
        default=None,
        help=argparse.SUPPRESS,  # 隐藏但兼容
    )
    parser.add_argument(
        "legacy_task",
        nargs="*",
        help=argparse.SUPPRESS,
    )

    parsed = parser.parse_args(args)

    # 构建 CliArgs
    cli = CliArgs(
        port=parsed.port,
        host=parsed.host,
        model=parsed.model,
        daemon=parsed.daemon,
        headless=parsed.headless,
        config=parsed.config,
        log_level=parsed.log_level,
    )

    # 确定 command
    if parsed.web_autostart:
        cli.command = "web_autostart"
        cli.web_autostart = parsed.web_autostart
    elif parsed.run_task is not None:
        cli.command = "run"
        if parsed.run_task:
            cli.task = [parsed.run_task]
    elif parsed.command:
        cli.command = parsed.command
    elif parsed.legacy_command and parsed.legacy_command in (
        "cli", "desktop", "web", "run", "setup", "integrity", "scheduler"
    ):
        # 兼容旧式: python main.py desktop / web
        cli.command = parsed.legacy_command
        if parsed.legacy_command == "run":
            cli.task = list(parsed.legacy_task)
    else:
        cli.command = "desktop"  # 默认桌面应用

    # headless 强依赖 daemon
    if cli.headless and not cli.daemon:
        cli.daemon = True

    return cli
    cli.command = "desktop"  # 默认桌面应用

    # headless 强依赖 daemon
    if cli.headless and not cli.daemon:
        cli.daemon = True

    return cli
