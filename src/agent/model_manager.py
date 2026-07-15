"""
模型管理器 — 统一 OpenAI 兼容 API 调用 + 成本追踪
支持: DeepSeek / OpenAI / Ollama / SiliconFlow / 豆包 / 自定义
详见架构文档 §15
"""
from typing import Any

from loguru import logger


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
    """统一的 LLM 模型管理"""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._client = None
        self._api_name = model_name  # API 实际调用的名称
        self.context_window = 128000
        self.max_tokens = 4096
        self.temperature = 0.7
        self._load_config_defaults()

    def _load_config_defaults(self):
        """从配置加载 context_window / max_tokens / temperature"""
        try:
            from ..config.loader import load_config
            config = load_config()
            ai_cfg = config.get("ai", {})
            # 兼容新格式（ai.configs）和旧格式（直接 ai.xxx）
            if "configs" in ai_cfg:
                active_key = ai_cfg.get("active", "deepseek")
                active_cfg = ai_cfg["configs"].get(active_key)
                # 如果 active 指向的配置不存在，回退到第一个可用配置
                if not active_cfg:
                    available = [k for k, v in ai_cfg["configs"].items() if v and isinstance(v, dict)]
                    if available:
                        active_key = available[0]
                        active_cfg = ai_cfg["configs"][active_key]
                    else:
                        active_cfg = {}
            else:
                active_cfg = ai_cfg
            self.context_window = active_cfg.get("context_window", ai_cfg.get("context_window", 128000))
            self.max_tokens = active_cfg.get("max_tokens", ai_cfg.get("max_tokens", 4096))
            self.temperature = active_cfg.get("temperature", ai_cfg.get("temperature", 0.7))
        except Exception as e:
            logger.warning(f"加载 AI 配置失败，使用默认值: {e}")

    def get_api_name(self) -> str:
        return self._api_name

    def chat(self, **kwargs) -> dict:
        """调用 LLM chat completion — 自动注入 context_window / max_tokens / temperature"""
        client = self._get_client()
        # 注入默认参数（允许调用方覆盖）
        kwargs.setdefault("model", self.model_name)
        kwargs.setdefault("max_tokens", self.max_tokens)
        kwargs.setdefault("temperature", self.temperature)
        return client.chat.completions.create(**kwargs)

    def _get_client(self):
        """获取 OpenAI 兼容客户端 — 统一从 config.ai 读取（兼容多配置格式，带缓存）"""
        if self._client is not None:
            return self._client

        from ..config.loader import load_config
        config = load_config()
        ai_cfg = config.get("ai", {})

        # 兼容新格式（ai.configs.active_key）和旧格式（ai.provider）
        if "configs" in ai_cfg:
            active_key = ai_cfg.get("active", "deepseek")
            active_cfg = ai_cfg["configs"].get(active_key)
            # 如果 active 指向的配置不存在，回退到第一个可用配置
            if not active_cfg:
                available = [k for k, v in ai_cfg["configs"].items() if v and isinstance(v, dict)]
                if available:
                    active_key = available[0]
                    active_cfg = ai_cfg["configs"][active_key]
                    logger.warning(f"配置 ai.active='{ai_cfg.get('active')}' 无效，已回退到 '{active_key}'")
                else:
                    active_cfg = {}
            provider = active_cfg.get("provider", "deepseek") if active_cfg else "deepseek"
            api_key = active_cfg.get("api_key", "") if active_cfg else ""
            base_url = (active_cfg.get("base_url", "") or "").strip() if active_cfg else ""
            if not api_key and provider != "ollama":
                logger.error(f"❌ 活跃模型 '{active_key}' 未配置 api_key，请检查 config.yaml 中 ai.configs.{active_key}.api_key")
        else:
            provider = ai_cfg.get("provider", "deepseek")
            api_key = ai_cfg.get("api_key", "")
            base_url = ai_cfg.get("base_url", "").strip()
            if not api_key and provider != "ollama":
                logger.error("❌ AI 配置中未找到 api_key，请检查 config.yaml 中 ai.api_key 或 ai.configs.<active>.api_key")

        if not api_key and provider != "ollama":
            raise ValueError(
                "AI API Key 未配置！\n"
                "请在设置页面的「AI 模型」Tab 中配置 API Key，\n"
                "或手动编辑 config/config.yaml 中的 api_key 字段。\n"
                "也可以切换到 Ollama 本地模型（无需 API Key）。"
            )

        import openai

        # 各 provider 的默认 base_url
        DEFAULT_URLS = {
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu":    "https://open.bigmodel.cn/api/paas/v4",
            "ollama":   "http://localhost:11434/v1",
        }

        final_url = base_url or DEFAULT_URLS.get(provider, "https://api.openai.com/v1")

        logger.info(f"🤖 连接 AI: provider={provider}, base_url={final_url}, api_key={'***' + api_key[-4:] if api_key and len(api_key) > 4 else '(none)'}")

        self._client = openai.OpenAI(api_key=api_key, base_url=final_url)
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
        _model_cache[model_name] = ModelManager(model_name)
        logger.debug(f"🤖 加载模型: {model_name}")
    return _model_cache[model_name]
