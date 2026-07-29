"""日志配置"""
import sys
import re
from pathlib import Path

from loguru import logger

# 控制台过滤规则：匹配这些模式的行不显示在控制台（文件日志不受影响）
_CONSOLE_FILTER_PATTERNS = [
    r"🔧\s*注册工具",
    r"📦\s*插件已加载",
    r"✅\s*数据库初始化完成",
    r"\[系统\]\s*(loguru|标准 logging|Python stdout|OS 管道).*已安装",
    r"\[系统\]\s*(loguru|GUI 模式).*跳过",
]


def _console_filter(record):
    """控制台过滤器：过滤掉启动噪音，文件日志不受影响。"""
    message = record["message"]
    for pattern in _CONSOLE_FILTER_PATTERNS:
        if re.search(pattern, message):
            return False
    return True


def setup_logging(level: str = "INFO", retention: str = "30 days",
                  rotation: str = "100 MB", log_dir: str = "./logs"):
    """初始化日志系统"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()

    # 控制台输出（彩色）— 带过滤器，屏蔽启动噪音
    if sys.stdout is not None:
        logger.add(
            sys.stdout,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            colorize=True,
            filter=_console_filter,
        )

    # 文件输出（所有级别，不过滤）
    logger.add(
        log_path / "app_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} | {message}",
        retention=retention,
        rotation=rotation,
        encoding="utf-8",
    )

    # 错误日志
    logger.add(
        log_path / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} | {message}\n{exception}",
        retention=retention,
        rotation=rotation,
        encoding="utf-8",
    )

    return logger
