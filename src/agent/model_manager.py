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
    "deepseek-v4-pro":     {"prompt": 1.0,  "completion": 4.0},
    "deepseek-reasoner": {"prompt": 4.0,  "completion": 16.0},
    "GLM-5.2":           {"prompt": 1.5,  "completion": 6.0},
    "kimi-k3":           {"prompt": 2.0,  "completion": 8.0},
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
        """从数据库加载 context_window / max_tokens / temperature / extra_config

        优先按 model_name 匹配 config_key，找不到则回退到活跃配置。
        """
        try:
            from ..database.db import get_ai_config_by_key, get_active_ai_config_raw
            cfg = get_ai_config_by_key(self.model_name)
            if not cfg:
                cfg = get_active_ai_config_raw()
            if cfg:
                self.context_window = cfg.get("context_window", 128000)
                self.max_tokens = cfg.get("max_tokens", 4096)
                self.temperature = cfg.get("temperature", 0.7)
                self.extra_config = cfg.get("extra_config") or {}
                self.provider = cfg.get("provider", "")
            else:
                logger.warning("未找到 AI 配置，使用默认值")
                self.extra_config = {}
                self.provider = ""
        except Exception as e:
            logger.warning(f"加载 AI 配置失败，使用默认值: {e}")
            self.extra_config = {}
            self.provider = ""

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
        # Kimi/Moonshot & DeepSeek: temperature 是固定值，不应显式传入
        if self.provider not in ("moonshot", "deepseek"):
            kwargs.setdefault("temperature", self.temperature)
        # 注入 extra_config（如 reasoning_effort 等扩展参数）
        for key, value in self.extra_config.items():
            kwargs.setdefault(key, value)

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
                if attempt >= 3:
                    break
                delay = min(2 * (2 ** attempt), 60) * (0.5 + random.random())
                logger.warning(
                    f"⚠️ 未知错误 (尝试 {attempt+1}/3): {e} — {delay:.1f}s 后重试"
                )
                time.sleep(delay)

        # 所有重试都失败
        raise RuntimeError(f"LLM 调用失败（已重试 5 次），最后错误: {last_error}")

    def _get_client(self):
        """懒加载创建 OpenAI 客户端"""
        if self._client is not None:
            return self._client

        from openai import OpenAI
        from ..config.loader import load_config

        cfg = load_config()
        ai_config = cfg.get("ai", {})
        active = ai_config.get("active", "deepseek")
        configs = ai_config.get("configs", {})
        model_cfg = configs.get(active, {})

        api_key = model_cfg.get("api_key", "")
        base_url = model_cfg.get("base_url", "https://api.deepseek.com/v1")

        if not api_key:
            raise RuntimeError(
                f"未配置 AI API Key！请设置 {active.upper()}_API_KEY 环境变量"
            )

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def _sanitize_tools(self, tools: list) -> list:
        """清理 tools 列表，移除不合法的字段

        OpenAI API 要求 function.parameters 必须是有效的 JSON Schema:
        - type 不能为 None/null
        - $defs 引用必须存在
        """
        sanitized = []
        for tool in tools:
            try:
                fn = tool.get("function", {})
                params = fn.get("parameters", {})
                if params:
                    # 递归清理 schema
                    params = self._clean_schema(params)
                    fn["parameters"] = params
                sanitized.append(tool)
            except Exception:
                sanitized.append(tool)
        return sanitized

    def _clean_schema(self, schema: dict) -> dict:
        """递归清理 JSON Schema，修复常见问题"""
        if not isinstance(schema, dict):
            return schema

        cleaned = {}
        for key, value in schema.items():
            if key == "type" and value is None:
                cleaned[key] = "object"  # 修复 type: null
            elif isinstance(value, dict):
                cleaned[key] = self._clean_schema(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_schema(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        return cleaned


# ===== 全局模型缓存 =====
_model_cache: dict[str, ModelManager] = {}


def get_model(model_name: str) -> ModelManager:
    """获取或创建模型管理器实例（全局单例缓存）"""
    if model_name not in _model_cache:
        logger.debug(f"🤖 加载模型: {model_name}")
        _model_cache[model_name] = ModelManager(model_name)
    else:
        logger.debug(f"🤖 模型已缓存: {model_name}")
    return _model_cache[model_name]


def clear_model_cache():
    """清除模型缓存（配置变更后调用）"""
    _model_cache.clear()
    logger.info("🔄 模型缓存已清除，下次请求将使用新配置")
