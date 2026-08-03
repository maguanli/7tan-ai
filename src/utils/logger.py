"""日志配置"""
import sys
import re
import logging
from datetime import datetime
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


_std_handler_installed = False


# 第三方库噪音静音清单：这些库的 DEBUG/INFO 日志量巨大且无排查价值
# （piper 会打印完整音素表 phonemes，几千字符/次），统一压制到 WARNING。
_NOISY_LOGGERS = [
    "piper",            # 合成时 DEBUG 打印 text + 完整 phonemes 音素表（巨型）
    "urllib3",          # HTTP 连接池 DEBUG（每次请求都打）
    "asyncio",          # proactor 等内部 DEBUG
    "uvicorn.access",   # 每个 HTTP 请求都打 INFO
    "uvicorn",
    "markdown",         # 扩展加载 DEBUG
    "httpx",
    "httpcore",
]


def silence_noisy_loggers() -> None:
    """将第三方噪音库的日志级别压制到 WARNING，业务日志不受影响。

    背景：piper 语音引擎在 synthesize() 时打印 DEBUG 日志
    （text=完整文本, phonemes=完整音素表，单条可达数千字符），
    由于标准 logging root 级别放开 DEBUG，这些巨型日志被写入
    文件/控制台，看起来像乱码刷屏。此处统一静音。
    """
    for name in _NOISY_LOGGERS:
        try:
            logging.getLogger(name).setLevel(logging.WARNING)
        except Exception:
            pass


def _install_std_file_handler(log_path: Path) -> None:
    """为标准 logging 添加文件 handler（agent_loop 等模块的可追溯性）。

    背景：agent_loop / speak_bridge 等用标准 logging 打印关键日志
    （💬 Agent、调用工具、迭代等），此前只有控制台可见、不进文件日志，
    导致问题排查完全黑盒。此处将标准 logging 同步写入文件。
    """
    global _std_handler_installed
    if _std_handler_installed:
        return
    _std_handler_installed = True
    try:
        handler = logging.FileHandler(
            log_path / f"std_python_{datetime.now():%Y-%m-%d}.log",
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
        ))
        root = logging.getLogger()
        root.addHandler(handler)
        logger.info(f"标准 logging 文件 handler 已安装: {log_path / ('std_python_' + datetime.now().strftime('%Y-%m-%d') + '.log')}")
    except Exception as e:
        logger.warning(f"标准 logging 文件 handler 安装失败: {e}")


def setup_logging(level: str = "INFO", retention: str = "30 days",
                  rotation: str = "100 MB", log_dir: str = "./logs"):
    """初始化日志系统"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()

    # 标准 logging → 文件（补齐 agent_loop 等标准 logging 模块的可追溯性）
    # agent_loop 用 logging.getLogger 打印 💬 Agent/调用工具 等关键日志，
    # 之前只进控制台不进文件 → 出问题完全无法排查（黑盒）
    _install_std_file_handler(log_path)

    # 静音第三方噪音库（piper 的 phonemes 巨型 DEBUG 等）
    silence_noisy_loggers()

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
