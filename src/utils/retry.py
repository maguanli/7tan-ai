"""
分级重试策略模块 v2
支持: 同步/异步、指数退避、智能抖动、错误分类、降级策略
详见架构文档 §7.1
"""
import functools
import time
import random
import asyncio
from typing import Callable, TypeVar, Any

from loguru import logger

F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    """重试配置"""
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 300.0, backoff: float = 2.0,
                 jitter: bool = True, retry_on: tuple = (Exception,),
                 name: str = ""):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff = backoff
        self.jitter = jitter
        self.retry_on = retry_on
        self.name = name


# ===== 预定义重试策略 =====

RETRY_POLICIES = {
    # AI API 调用 — 网络超时/服务波动
    "api_timeout":    RetryConfig(max_retries=5, base_delay=2, max_delay=120, backoff=2.0,
                                  name="API超时"),
    # API 限流 — 等久一点
    "api_rate_limit": RetryConfig(max_retries=30, base_delay=60, max_delay=600, backoff=1.0,
                                  name="API限流"),
    # 文件下载 — 快速重试
    "download":       RetryConfig(max_retries=3, base_delay=1, max_delay=30, backoff=1.0,
                                  name="下载失败"),
    # 浏览器崩溃 — 等一会儿重新来
    "browser_crash":  RetryConfig(max_retries=2, base_delay=30, max_delay=120, backoff=1.0,
                                  name="浏览器崩溃"),
    # 登录失败
    "login":          RetryConfig(max_retries=3, base_delay=120, max_delay=600, backoff=1.5,
                                  name="登录失败"),
    # 站点宕机 — 长时间等待
    "site_down":      RetryConfig(max_retries=999, base_delay=600, max_delay=3600, backoff=1.0,
                                  name="站点宕机"),
    # 磁盘满了 — 不重试
    "disk_full":      RetryConfig(max_retries=0, base_delay=0, max_delay=0, backoff=1.0,
                                  name="磁盘已满"),
    # 验证码 — 不重试
    "captcha":        RetryConfig(max_retries=0, base_delay=0, max_delay=0, backoff=1.0,
                                  name="需要验证码"),
    # 通用网络错误 — 适度重试
    "network":        RetryConfig(max_retries=4, base_delay=1, max_delay=60, backoff=2.0,
                                  name="网络错误"),
    # 数据库操作
    "database":       RetryConfig(max_retries=3, base_delay=0.5, max_delay=10, backoff=2.0,
                                  name="数据库错误"),
}


class RetryExhausted(Exception):
    """重试耗尽异常"""
    def __init__(self, message: str, last_error: Exception = None):
        super().__init__(message)
        self.last_error = last_error


# ===== 智能错误分类 =====

# 不应重试的错误类型
NON_RETRYABLE_ERRORS = (
    ValueError,
    TypeError,
    AttributeError,
    KeyError,
    IndexError,
    FileNotFoundError,
    PermissionError,
    NotImplementedError,
    ImportError,
    ModuleNotFoundError,
    SyntaxError,
    IndentationError,
)

# 可重试的网络相关错误关键词
RETRYABLE_KEYWORDS = [
    "timeout", "timed out", "connection", "reset", "refused",
    "unreachable", "502", "503", "504", "429", "too many",
    "rate limit", "throttl", "server error", "internal server",
    "service unavailable", "bad gateway", "gateway timeout",
    "temporary", "retry", "overloaded", "capacity", "busy",
]


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否应该重试"""
    # 不可重试的类型直接拒绝
    if isinstance(error, NON_RETRYABLE_ERRORS):
        return False

    # 检查错误消息中的关键词
    error_str = str(error).lower()
    for kw in RETRYABLE_KEYWORDS:
        if kw in error_str:
            return True

    # HTTP 错误码检查
    if hasattr(error, "status_code"):
        code = getattr(error, "status_code", 0)
        if code in (429, 500, 502, 503, 504):
            return True

    if hasattr(error, "http_status"):
        code = getattr(error, "http_status", 0)
        if code in (429, 500, 502, 503, 504):
            return True

    return False


def classify_policy(error: Exception) -> str:
    """根据错误类型自动选择重试策略"""
    error_str = str(error).lower()

    if "rate" in error_str or "429" in error_str or "throttl" in error_str:
        return "api_rate_limit"
    if "timeout" in error_str or "timed out" in error_str:
        return "api_timeout"
    if "connection" in error_str or "refused" in error_str or "reset" in error_str:
        return "network"
    if "disk" in error_str or "space" in error_str:
        return "disk_full"

    return "api_timeout"  # 默认


# ===== 同步重试装饰器 =====

def retry(policy: str = "api_timeout", on_failure: str = "raise",
          auto_classify: bool = True):
    """
    同步重试装饰器

    Args:
        policy: 策略名（见 RETRY_POLICIES）, 或传入 RetryConfig 实例
        on_failure: 耗尽后行为: 'raise'(默认) | 'return_none' | 'skip'
        auto_classify: 是否根据错误自动选择策略
    """
    if isinstance(policy, RetryConfig):
        cfg = policy
    else:
        cfg = RETRY_POLICIES.get(policy, RETRY_POLICIES["api_timeout"])

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            effective_cfg = cfg

            for attempt in range(cfg.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except cfg.retry_on as e:
                    last_error = e

                    # 自动分类：根据错误选择更合适的策略
                    if auto_classify and is_retryable_error(e):
                        policy_name = classify_policy(e)
                        effective_cfg = RETRY_POLICIES.get(policy_name, cfg)
                    elif not is_retryable_error(e):
                        # 不可重试的错误直接抛出
                        logger.error(f"❌ {func.__name__} 遇到不可重试错误: {e}")
                        raise

                    if attempt >= effective_cfg.max_retries:
                        logger.error(
                            f"❌ {func.__name__} 重试{effective_cfg.max_retries}次后仍失败 "
                            f"({effective_cfg.name}): {e}"
                        )
                        if on_failure == "raise":
                            raise RetryExhausted(
                                f"{func.__name__} 重试耗尽 ({effective_cfg.max_retries}次)",
                                last_error=e
                            ) from e
                        elif on_failure in ("return_none", "skip"):
                            logger.warning(f"⏭️ 跳过 {func.__name__}: {e}")
                            return None
                    else:
                        delay = min(
                            effective_cfg.base_delay * (effective_cfg.backoff ** attempt),
                            effective_cfg.max_delay
                        )
                        if effective_cfg.jitter:
                            delay = delay * (0.5 + random.random())
                        logger.warning(
                            f"🔄 {func.__name__} 失败 (尝试 {attempt+1}/{effective_cfg.max_retries}): "
                            f"{type(e).__name__}: {str(e)[:100]} — {delay:.1f}s 后重试 "
                            f"[策略: {effective_cfg.name}]"
                        )
                        time.sleep(delay)
            return None
        return wrapper  # type: ignore
    return decorator


# ===== 异步重试装饰器 =====

def async_retry(policy: str = "api_timeout", on_failure: str = "raise",
                auto_classify: bool = True):
    """
    异步重试装饰器

    Args:
        policy: 策略名（见 RETRY_POLICIES）
        on_failure: 'raise' | 'return_none' | 'skip'
        auto_classify: 是否根据错误自动选择策略
    """
    if isinstance(policy, RetryConfig):
        cfg = policy
    else:
        cfg = RETRY_POLICIES.get(policy, RETRY_POLICIES["api_timeout"])

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            effective_cfg = cfg

            for attempt in range(cfg.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except cfg.retry_on as e:
                    last_error = e

                    if auto_classify and is_retryable_error(e):
                        policy_name = classify_policy(e)
                        effective_cfg = RETRY_POLICIES.get(policy_name, cfg)
                    elif not is_retryable_error(e):
                        logger.error(f"❌ {func.__name__} 遇到不可重试错误: {e}")
                        raise

                    if attempt >= effective_cfg.max_retries:
                        logger.error(
                            f"❌ {func.__name__} 重试{effective_cfg.max_retries}次后仍失败 "
                            f"({effective_cfg.name}): {e}"
                        )
                        if on_failure == "raise":
                            raise RetryExhausted(
                                f"{func.__name__} 重试耗尽 ({effective_cfg.max_retries}次)",
                                last_error=e
                            ) from e
                        elif on_failure in ("return_none", "skip"):
                            logger.warning(f"⏭️ 跳过 {func.__name__}: {e}")
                            return None
                    else:
                        delay = min(
                            effective_cfg.base_delay * (effective_cfg.backoff ** attempt),
                            effective_cfg.max_delay
                        )
                        if effective_cfg.jitter:
                            delay = delay * (0.5 + random.random())
                        logger.warning(
                            f"🔄 {func.__name__} 失败 (尝试 {attempt+1}/{effective_cfg.max_retries}): "
                            f"{type(e).__name__}: {str(e)[:100]} — {delay:.1f}s 后重试 "
                            f"[策略: {effective_cfg.name}]"
                        )
                        await asyncio.sleep(delay)
            return None
        return wrapper  # type: ignore
    return decorator


# ===== 快捷重试函数 =====

def retry_call(func: Callable, *args, policy: str = "api_timeout",
               on_failure: str = "raise", **kwargs) -> Any:
    """直接调用带重试的函数（无需装饰器）"""
    cfg = RETRY_POLICIES.get(policy, RETRY_POLICIES["api_timeout"])
    last_error = None
    effective_cfg = cfg

    for attempt in range(cfg.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except cfg.retry_on as e:
            last_error = e

            if is_retryable_error(e):
                policy_name = classify_policy(e)
                effective_cfg = RETRY_POLICIES.get(policy_name, cfg)
            elif not is_retryable_error(e):
                raise

            if attempt >= effective_cfg.max_retries:
                if on_failure == "raise":
                    raise RetryExhausted(
                        f"{func.__name__} 重试耗尽", last_error=e
                    ) from e
                return None
            else:
                delay = min(
                    effective_cfg.base_delay * (effective_cfg.backoff ** attempt),
                    effective_cfg.max_delay
                )
                if effective_cfg.jitter:
                    delay = delay * (0.5 + random.random())
                logger.warning(
                    f"🔄 {func.__name__} 失败 (尝试 {attempt+1}/{effective_cfg.max_retries}): "
                    f"{type(e).__name__} — {delay:.1f}s 后重试"
                )
                time.sleep(delay)
    return None


async def async_retry_call(func: Callable, *args, policy: str = "api_timeout",
                           on_failure: str = "raise", **kwargs) -> Any:
    """直接调用带异步重试的函数"""
    cfg = RETRY_POLICIES.get(policy, RETRY_POLICIES["api_timeout"])
    last_error = None
    effective_cfg = cfg

    for attempt in range(cfg.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except cfg.retry_on as e:
            last_error = e

            if is_retryable_error(e):
                policy_name = classify_policy(e)
                effective_cfg = RETRY_POLICIES.get(policy_name, cfg)
            elif not is_retryable_error(e):
                raise

            if attempt >= effective_cfg.max_retries:
                if on_failure == "raise":
                    raise RetryExhausted(
                        f"{func.__name__} 重试耗尽", last_error=e
                    ) from e
                return None
            else:
                delay = min(
                    effective_cfg.base_delay * (effective_cfg.backoff ** attempt),
                    effective_cfg.max_delay
                )
                if effective_cfg.jitter:
                    delay = delay * (0.5 + random.random())
                logger.warning(
                    f"🔄 {func.__name__} 失败 (尝试 {attempt+1}/{effective_cfg.max_retries}): "
                    f"{type(e).__name__} — {delay:.1f}s 后重试"
                )
                await asyncio.sleep(delay)
    return None
