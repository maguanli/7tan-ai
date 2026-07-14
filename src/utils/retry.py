"""
分级重试策略模块
支持指数退避、最大重试、降级策略
"""
import functools
import time
import random

from loguru import logger


class RetryConfig:
    """重试配置"""
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 300.0, backoff: float = 2.0,
                 jitter: bool = True, retry_on: tuple = (Exception,)):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff = backoff
        self.jitter = jitter
        self.retry_on = retry_on


# 预定义重试策略（对应架构文档 §7.1）
RETRY_POLICIES = {
    "api_timeout":    RetryConfig(max_retries=5, base_delay=2, max_delay=120, backoff=2.0),
    "api_rate_limit": RetryConfig(max_retries=3, base_delay=60, max_delay=600, backoff=1.0),
    "download":       RetryConfig(max_retries=3, base_delay=1, max_delay=30, backoff=1.0),
    "browser_crash":  RetryConfig(max_retries=2, base_delay=30, max_delay=120, backoff=1.0),
    "login":          RetryConfig(max_retries=3, base_delay=120, max_delay=600, backoff=1.5),
    "site_down":      RetryConfig(max_retries=999, base_delay=600, max_delay=3600, backoff=1.0),
    "disk_full":      RetryConfig(max_retries=1, base_delay=0, max_delay=0, backoff=1.0),
    "captcha":        RetryConfig(max_retries=0, base_delay=0, max_delay=0, backoff=1.0),
}


class RetryExhausted(Exception):
    """重试耗尽异常"""
    def __init__(self, message: str, last_error: Exception = None):
        super().__init__(message)
        self.last_error = last_error


def retry(policy: str = "api_timeout", on_failure: str = "raise"):
    """
    重试装饰器

    Args:
        policy: 策略名（见 RETRY_POLICIES）, 或传入 RetryConfig 实例
        on_failure: 耗尽后行为: 'raise'(默认) | 'return_none' | 'skip'
    """
    cfg = RETRY_POLICIES.get(policy, policy)
    if not isinstance(cfg, RetryConfig):
        cfg = RETRY_POLICIES["api_timeout"]

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(cfg.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except cfg.retry_on as e:
                    last_error = e
                    if attempt >= cfg.max_retries:
                        logger.error(f"❌ {func.__name__} 重试{cfg.max_retries}次后仍失败: {e}")
                        if on_failure == "raise":
                            raise RetryExhausted(
                                f"{func.__name__} 重试耗尽 ({cfg.max_retries}次)",
                                last_error=e
                            ) from e
                        elif on_failure == "return_none":
                            return None
                        elif on_failure == "skip":
                            logger.warning(f"⏭️ 跳过 {func.__name__}: {e}")
                            return None
                    else:
                        delay = min(cfg.base_delay * (cfg.backoff ** attempt), cfg.max_delay)
                        if cfg.jitter:
                            delay = delay * (0.5 + random.random())
                        logger.warning(
                            f"🔄 {func.__name__} 失败 (尝试 {attempt+1}/{cfg.max_retries}): {e}"
                            f" — {delay:.1f}s 后重试"
                        )
                        time.sleep(delay)
            return None
        return wrapper
    return decorator
