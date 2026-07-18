"""
模型管理器 — 统一 OpenAI 兼容 API 调用 + 成本追踪 + 智能重试
支持: DeepSeek / OpenAI / Ollama / SiliconFlow / 豆包 / 自定义
详见架构文档 §15
"""
from typing import Any

from loguru import logger

from ..utils.retry import retry, is_retryable_error, classify_policy, RETRY_POLICIES


# ===== 各模型价格（每百万 token，人民币，参考各厂商公开定价）=====

MODEL_PRICES = {
    "deepseek-v4-pro":   {"prompt": 2.0,  "completion": 8.0},
    "deepseek-v4-flash": {"prompt": 0.5,  "completion": 2.0},
    "GLM-5.2":           {"prompt": 1.5,  "completion": 6.0},
}


class CostTracker:
    """记录每次 API 调用的 token 和费用"""

    @staticmethod
    def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """估算费用（人民币）"""
        price = MODEL_PRICES.get(model, {"prompt": 1.0, "completion": 4.0})
        return round(
            (prompt_tokens / 1_000_000 * price["prompt"] +
             completion_tokens / 1_000_000 * price["completion"]),
            6,
        )

    @staticmethod
    def record_usage(model: str, prompt_tokens: int, completion_tokens: int):
        """记录用量到文件"""
        cost = CostTracker.estimate_cost(model, prompt_tokens, completion_tokens)
        logger.debug(
            f"💰 [{model}] prompt={prompt_tokens}, completion={completion_tokens}, "
            f"total_tokens={prompt_tokens + completion_tokens}, cost=¥{cost:.4f}"
        )
        return cost


class ModelManager:
    """统一的 LLM 模型管理（带智能重试）"""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._client = None
        self._api_name = model_name  # API 实际调用的名称
        self.context_window = 128000
        self.max_tokens = 16384
        self.temperature = 0.7
        self._load_config_defaults()

    def _load_config_defaults(self):
        """从数据库加载 context_window / max_tokens / temperature"""
        try:
            from ..database.db import get_active_ai_config_raw
            cfg = get_active_ai_config_raw()
            if cfg:
                self.context_window = cfg.get("context_window", 128000)
                self.max_tokens = cfg.get("max_tokens", 4096)
                self.temperature = cfg.get("temperature", 0.7)
            else:
                logger.warning("未找到活跃 AI 配置，使用默认值")
        except Exception as e:
            logger.warning(f"加载 AI 配置失败，使用默认值: {e}")

    def get_api_name(self) -> str:
        return self._api_name

    def chat(self, **kwargs) -> dict:
        """
        调用 LLM chat completion — 带智能重试
        
        自动根据错误类型选择重试策略：
        - 超时 → api_timeout (5次, 2s起步, 指数退避)
        - 限流/429 → api_rate_limit (3次, 60s起步)
        - 连接错误 → network (4次, 1s起步)
        - HTTP 5xx → api_timeout
        - 400 (参数错误) → 不重试，直接抛出
        """
        client = self._get_client()
        # 注入默认参数（允许调用方覆盖）
        kwargs.setdefault("model", self.model_name)
        kwargs.setdefault("max_tokens", self.max_tokens)
        kwargs.setdefault("temperature", self.temperature)

        # 🔒 安全校验：确保所有 tools 的 schema 合法（防止 type: null 等 400 错误）
        if "tools" in kwargs:
            kwargs["tools"] = self._sanitize_tools(kwargs["tools"])

        return self._chat_with_retry(client, **kwargs)

    def _chat_with_retry(self, client, **kwargs):
        """带智能重试的 chat 调用"""
        import time
        import random
        from openai import (
            APIError, APITimeoutError, APIConnectionError,
            RateLimitError, InternalServerError, BadRequestError
        )

        last_error = None

        for attempt in range(4):  # 最多 5 次重试 (0~5)
            try:
                return client.chat.completions.create(**kwargs)
            except BadRequestError as e:
                # 400 错误不重试（参数/格式问题）
                logger.error(f"❌ API 请求参数错误 (400): {e}")
                raise
            except RateLimitError as e:
                last_error = e
                if attempt >= 3:
                    break
                delay = min(30 * (2 ** attempt), 300) * (0.5 + random.random())
                logger.warning(
                    f"⏳ API 限流 (尝试 {attempt+1}/3)，{delay:.1f}s 后重试..."
                )
                time.sleep(delay)
            except APITimeoutError as e:
                last_error = e
                if attempt >= 3:
                    break
                delay = min(2 * (2 ** attempt), 60) * (0.5 + random.random())
                logger.warning(
                    f"⏱️ API 超时 (尝试 {attempt+1}/3)，{delay:.1f}s 后重试..."
                )
                time.sleep(delay)
            except APIConnectionError as e:
                last_error = e
                if attempt >= 3:
                    break
                delay = min(1 * (2 ** attempt), 30) * (0.5 + random.random())
                logger.warning(
                    f"🔌 API 连接错误 (尝试 {attempt+1}/3)，{delay:.1f}s 后重试..."
                )
                time.sleep(delay)
            except InternalServerError as e:
                last_error = e
                if attempt >= 3:
                    break
                delay = min(2 * (2 ** attempt), 60) * (0.5 + random.random())
                logger.warning(
                    f"🔥 API 服务器错误 (尝试 {attempt+1}/3)，{delay:.1f}s 后重试..."
                )
                time.sleep(delay)
            except APIError as e:
                last_error = e
                err_str = str(e).lower()
                # 检查是否是 HTTP 状态码错误
                if "502" in err_str or "503" in err_str or "504" in err_str:
                    if attempt >= 3:
                        break
                    delay = min(3 * (2 ** attempt), 60) * (0.5 + random.random())
                    logger.warning(
                        f"🌐 API 网关错误 (尝试 {attempt+1}/3)，{delay:.1f}s 后重试..."
                    )
                    time.sleep(delay)
                elif "429" in err_str:
                    if attempt >= 3:
                        break
                    delay = min(30 * (2 ** attempt), 300) * (0.5 + random.random())
                    logger.warning(
                        f"⏳ API 限流 (尝试 {attempt+1}/3)，{delay:.1f}s 后重试..."
                    )
                    time.sleep(delay)
                else:
                    # 未知 API 错误也重试
                    if attempt >= 3:
                        break
                    delay = min(2 * (2 ** attempt), 60) * (0.5 + random.random())
                    logger.warning(
                        f"⚠️ API 错误 (尝试 {attempt+1}/3): {e} — {delay:.1f}s 后重试"
                    )
                    time.sleep(delay)
            except Exception as e:
                # 其他未知错误（如网络波动导致的底层异常）
                last_error = e
                err_str = str(e).lower()
                if any(kw in err_str for kw in ("ssl", "connection", "timeout", "reset", "refused", "broken pipe")):
                    if attempt >= 3:
                        break
                    delay = min(2 * (2 ** attempt), 60) * (0.5 + random.random())
                    logger.warning(
                        f"🔧 网络层错误 (尝试 {attempt+1}/3): {type(e).__name__} — {delay:.1f}s 后重试"
                    )
                    time.sleep(delay)
                else:
                    # 不认识的异常不重试
                    logger.error(f"❌ 未知错误，不重试: {type(e).__name__}: {e}")
                    raise

        # 重试耗尽
        logger.error(f"💀 API 调用失败，已重试 3 次: {last_error}")
        raise RuntimeError(
            f"AI API 调用失败（已重试 3 次）: {last_error}"
        ) from last_error

    @staticmethod
    def _sanitize_tools(tools: list) -> list:
        """修复 tools 列表中不完整的 function schema"""
        sanitized = []
        for tool in tools:
            try:
                fn = tool.get("function", {})
                params = fn.get("parameters")
                if not isinstance(params, dict) or not params.get("type"):
                    fn = dict(fn)
                    fn["parameters"] = {"type": "object", "properties": {}, "required": []}
                    tool = dict(tool)
                    tool["function"] = fn
                    logger.warning(f"🔧 修复工具 schema: {fn.get('name', 'unknown')} (type was: {type(params).__name__})")
                sanitized.append(tool)
            except Exception:
                sanitized.append(tool)
        return sanitized

    def _get_client(self):
        """获取 OpenAI 兼容客户端 — 从数据库读取活跃 AI 配置（带缓存）"""
        if self._client is not None:
            return self._client

        from ..database.db import get_active_ai_config_raw, get_all_ai_configs

        cfg = get_active_ai_config_raw()
        if not cfg:
            # 回退：尝试从数据库加载任何配置
            configs = get_all_ai_configs(mask_secrets=False)
            if configs:
                cfg = configs[0]
                logger.warning(f"没有活跃配置，回退到: {cfg.get('config_key')}")

        if cfg:
            provider = cfg.get("provider", "deepseek")
            api_key = cfg.get("api_key", "")
            base_url = (cfg.get("base_url", "") or "").strip()
            config_key = cfg.get("config_key", "unknown")
        else:
            provider = "deepseek"
            api_key = ""
            base_url = ""
            config_key = "none"

        if not api_key and provider != "ollama":
            raise ValueError(
                "AI API Key 未配置！\n"
                "请在「AI 设置」对话框中配置 API Key，\n"
                "或切换到 Ollama 本地模型（无需 API Key）。"
            )

        import openai
        import httpx

        # 各 provider 的默认 base_url
        DEFAULT_URLS = {
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu":    "https://open.bigmodel.cn/api/paas/v4",
            "ollama":   "http://localhost:11434/v1",
        }

        final_url = base_url or DEFAULT_URLS.get(provider, "https://api.openai.com/v1")

        logger.info(f"🤖 连接 AI [{config_key}]: provider={provider}, model={cfg.get('model','?') if cfg else '?'}, base_url={final_url}")

        # 🔒 配置 HTTP 超时，防止 AI API 调用无限挂起
        # connect=10s（建连接）, read=120s（等响应）, write=30s（发请求）
        # 单次调用最长 120s，配合重试 5 次，理论最大 ~10 分钟
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=final_url,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
        )
        return self._client


# 缓存已创建的模型实例
_model_cache = {}


def clear_model_cache():
    """清除所有缓存的模型客户端（配置更新后调用）"""
    for mgr in _model_cache.values():
        mgr._client = None
    _model_cache.clear()
    logger.info("🔄 模型缓存已清除，下次请求将使用新配置")


def get_model(model_name: str) -> ModelManager:
    """获取模型实例（带缓存）"""
    if model_name not in _model_cache:
        import sys
        logger.debug(f"🤖 加载模型: {model_name}")
        sys.stderr.flush()
        _model_cache[model_name] = ModelManager(model_name)
        logger.debug(f"🤖 模型已缓存: {model_name}")
        sys.stderr.flush()
    return _model_cache[model_name]
