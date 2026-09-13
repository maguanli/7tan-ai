"""
模型管理器 — 统一 OpenAI 兼容 API 调用 + 成本追踪 + 智能重试
支持: DeepSeek / OpenAI / Ollama / SiliconFlow / 豆包 / 自定义
详见架构文档 §15
"""
from typing import Any

from loguru import logger

from ..utils.retry import retry, is_retryable_error, classify_policy, RETRY_POLICIES, RetryConfig, RetryExhausted


# LLM 调用重试策略（统一走 utils/retry.py，避免手写重试循环）
# 2026-08-14 修复：偶发网络故障（APIConnectionError）可持续 1~5 分钟，
# 原 5 次重试（约 62s）窗口太短，故障稍长就报错。调至 8 次（约 6 分钟）覆盖短时波动。
_LLM_RETRY_CFG = RetryConfig(
    max_retries=8,
    base_delay=2.0,
    max_delay=120.0,
    backoff=2.0,
    jitter=True,
    name="LLM调用",
)


def _fix_surrogates(s: str) -> str:
    """清理字符串中的代理字符（surrogates）。
    
    有效代理对（如 \ud83d\ude00）→ 实际 Unicode 字符，
    孤立代理（如 \ud83d）→ '?'。
    结果可安全编码为 UTF-8。
    """
    # Fast path: check if string contains any surrogates at all
    if not any(0xD800 <= ord(ch) <= 0xDFFF for ch in s):
        return s

    result = []
    i = 0
    n = len(s)
    while i < n:
        code = ord(s[i])
        if 0xD800 <= code <= 0xDBFF:  # High surrogate
            if i + 1 < n and 0xDC00 <= ord(s[i+1]) <= 0xDFFF:
                try:
                    pair = s[i:i+2]
                    actual = pair.encode('utf-16', 'surrogatepass').decode('utf-16')
                    result.append(actual)
                except Exception:
                    result.append('?')
                i += 2
            else:
                result.append('?')
                i += 1
        elif 0xDC00 <= code <= 0xDFFF:  # Lone low surrogate
            result.append('?')
            i += 1
        else:
            result.append(chr(code))
            i += 1
    return ''.join(result)
# ===== 各模型价格（每百万 token，人民币，参考各厂商公开定价）=====

MODEL_PRICES = {
    "deepseek-flash":     {"prompt": 1.0,  "completion": 2.0},
    "deepseek-v4-flash":   {"prompt": 1.0,  "completion": 2.0},
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
def track_cost_internal(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """记录 API 调用费用（agent_loop 内部使用）"""
    return CostTracker.estimate_cost(model, prompt_tokens, completion_tokens)

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
        if model_name == "DeepSeek-V4-Flash-0731":
            model_name = "deepseek-v4-flash"
            self.model_name = model_name
        self._client = None
        self._api_name = model_name  # API 实际调用的名称
        # V4-Flash-0731 专属默认值（1M 上下文 / 384K 输出 / temp=1.0 / reasoning_effort=max）
        if model_name == "deepseek-v4-flash":
            self.context_window = 1_000_000
            self.max_tokens = 384_000
            self.temperature = 1.0
            self.extra_config = {"reasoning_effort": "max"}
        else:
            self.context_window = 128000
            self.max_tokens = 16384
            self.temperature = 0.25
            self.extra_config = {}
        # 🔒 在加载 DB 配置前先设一个安全上限（provider 未知时用保守值）
        self._provider_cap_applied = False
        self._load_config_defaults()
        # 🔒 DB 加载后再检查一次（防止 DB 返回超限值或 DB 加载失败）
        if not self._provider_cap_applied:
            cap = self._resolve_max_tokens_cap()
            if self.max_tokens > cap:
                logger.warning(f"⚠️ max_tokens {self.max_tokens} 超过 {getattr(self, 'provider', 'unknown')} 上限 {cap}，已自动限制")
                self.max_tokens = cap
        # 🔒 商汤(SenseNova)参数兼容：reasoning_effort 只接受 low/medium/high/xhigh/none
        #    官方 DeepSeek 的 "max" 在商汤接口会 400 InvalidParameter，初始化后统一修正
        if getattr(self, 'provider', '') == 'sensetime':
            self._sanitize_reasoning_effort(extra_config=self.extra_config)

    @staticmethod
    def _sanitize_reasoning_effort(extra_config=None, kwargs=None):
        """将 reasoning_effort 修正为供应商接受的合法值

        商汤(SenseNova)接口仅接受 low/medium/high/xhigh/none，
        官方 DeepSeek 的 "max" 在商汤会 400 InvalidParameter。
        修改 extra_config（返回 dict）或 kwargs（就地修改）。
        """
        allowed = {"low", "medium", "high", "xhigh", "none"}
        if kwargs is not None:
            effort = kwargs.get("reasoning_effort")
            if effort is not None and effort not in allowed:
                logger.warning(f"⚠️ 商汤接口不识别 reasoning_effort={effort!r}，已自动改为 'high'")
                kwargs["reasoning_effort"] = "high"
        if extra_config is not None:
            effort = extra_config.get("reasoning_effort")
            if effort is not None and effort not in allowed:
                logger.warning(f"⚠️ 商汤接口不识别 reasoning_effort={effort!r}，已自动改为 'high'")
                extra_config["reasoning_effort"] = "high"
        return extra_config
    # 🔒 供应商级别 max_tokens 安全上限（防止 API 400 错误）
    _PROVIDER_MAX_TOKENS_CAP = {
        "doubao": 4096,         # 豆包/火山引擎: max_tokens ≤ 4096
        "zhipu": 4096,          # 智谱 GLM: 部分模型 ≤ 4096
        "sensetime": 4096,      # 商汤: 部分模型 ≤ 4096
        "mimo": 16384,          # 小米 MiMo: 较宽松
        "moonshot": 16384,      # Kimi/Moonshot
        "deepseek": 131072,     # DeepSeek: 高上限
        "local_7tan_model": 16384,  # 本地 7Tan 模型：不受 API 限制
    }

    def _resolve_max_tokens_cap(self) -> int:
        """按 模型→供应商 解析 max_tokens 安全上限

        商汤免费额度模型（deepseek-v4-flash / glm-5.2）支持 65K+ 输出，
        不受 sensetime 4096 通用限制；其余模型仍按供应商上限熔断。
        """
        prov = getattr(self, 'provider', '') or ''
        mname = getattr(self, 'model_name', '') or ''
        if prov == 'sensetime' and mname in ('deepseek-v4-flash', 'glm-5.2'):
            return 65536
        if prov == 'zhipu' and mname in ('glm-5.2', 'glm-5.3', 'glm-5.3-flash', 'glm-5.3-flash-250828'):
            return 131072
        return self._PROVIDER_MAX_TOKENS_CAP.get(prov, 4096)

    def _load_config_defaults(self):
        """从数据库加载 context_window / max_tokens / temperature / extra_config"""
        try:
            from ..database.db import get_ai_config_by_key, get_active_ai_config_raw
            cfg = get_ai_config_by_key(self.model_name)
            # 🔧 第2步: 按 model 字段查找（解决 config_key ≠ model_name 的问题）
            if not cfg:
                try:
                    from ..database.db import get_session, AiConfig
                    session = get_session()
                    try:
                        # 优先活跃配置（用户切换后的目标模型），其次取最新配置
                        row = session.query(AiConfig).filter(
                            AiConfig.model == self.model_name,
                            AiConfig.is_active == 1
                        ).first()
                        if not row:
                            row = session.query(AiConfig).filter(
                                AiConfig.model == self.model_name
                            ).order_by(AiConfig.id.desc()).first()
                        if row:
                            cfg = row.to_dict(mask_secrets=False)
                    finally:
                        session.close()
                except Exception:
                    pass
            # 🔧 第3步: 回退到活跃配置
            if not cfg:
                cfg = get_active_ai_config_raw()
            if cfg:
                self.context_window = cfg.get("context_window", self.context_window)
                self.max_tokens = cfg.get("max_tokens", self.max_tokens)
                self.temperature = cfg.get("temperature", self.temperature)
                db_extra = cfg.get("extra_config")
                if db_extra:
                    self.extra_config = db_extra
                # 否则保留 __init__ 中的默认值（如 V4-Flash 的 reasoning_effort）
                self.provider = cfg.get("provider", "")
                self._db_api_key = cfg.get("api_key", "")  # 缓存 DB 中的 api_key
                self._db_base_url = cfg.get("base_url", "")
                # 🔒 供应商级 max_tokens 熔断：不超过 API 实际上限
                cap = self._resolve_max_tokens_cap()
                if self.max_tokens > cap:
                    logger.warning(f"⚠️ max_tokens {self.max_tokens} 超过 {self.provider} 上限 {cap}，已自动限制")
                    self.max_tokens = cap
                self._provider_cap_applied = True
            else:
                logger.warning("未找到 AI 配置，使用默认值")
                # 不覆盖 __init__ 中的 extra_config 默认值
                self.provider = ""
                self._db_api_key = ""
                self._db_base_url = ""
        except Exception as e:
            logger.warning(f"加载 AI 配置失败，使用默认值: {e}")
            self.extra_config = {}
            self.provider = ""
            self._db_api_key = ""
            self._db_base_url = ""

    def get_api_name(self) -> str:
        return self._api_name

    def call_with_retry(self, messages, tools=None, config=None, timeout=600):
        """兼容旧 agent_loop 调用接口 → 委托给 chat()"""
        kwargs = {"messages": messages}
        if tools:
            kwargs["tools"] = tools
        if config:
            kwargs.update(config)
        return self.chat(**kwargs)

    def chat(self, **kwargs) -> dict:
        """
        调用 LLM chat completion — 带智能重试
        
        自动根据错误类型选择重试策略：
        - 超时 → api_timeout (5次, 2s起步, 指数退避)
        - 限流/429 → api_rate_limit (30次, 60s起步)
        - 连接错误 → network (4次, 1s起步)
        - HTTP 5xx → api_timeout
        - 400 (参数错误) → 不重试，直接抛出
        """
        client = self._get_client()

        # 试用模式：走服务端代理，跳过 retry（trial.php 自带错误处理）
        if getattr(self, '_trial_mode', False):
            return self._trial_chat(**kwargs)

        # 注入默认参数（允许调用方覆盖）
        kwargs.setdefault("model", self.model_name)
        kwargs.setdefault("max_tokens", self.max_tokens)
        # Kimi/Moonshot: temperature 必须显式设为 1（Kimi K3 要求）
        # DeepSeek: temperature=0.3，平衡创造性与确定性
        if self.provider == "moonshot":
            kwargs["temperature"] = 1
        elif self.provider == "deepseek":
            kwargs.setdefault("temperature", 0.3)
        else:
            kwargs.setdefault("temperature", self.temperature)
        # 注入 extra_config（如 reasoning_effort 等扩展参数）
        # 🔒 仅注入 OpenAI chat completion 支持的扩展参数，
        #    过滤配置元数据（key_name/task_type/endpoint/watermark/size/note 等），
        #    防止透传给 SDK 导致 TypeError: unexpected keyword argument
        _LLM_EXTRA_WHITELIST = {
            "reasoning_effort", "max_completion_tokens", "response_format",
            "stop", "logprobs", "top_logprobs", "user", "stream_options",
        }
        for key, value in self.extra_config.items():
            if key in _LLM_EXTRA_WHITELIST:
                kwargs.setdefault(key, value)

        # 🔒 商汤(SenseNova)参数兼容兜底：无论 extra_config 来自哪（默认值/DB），
        #    传给商汤前一律把 reasoning_effort 修正为合法值（low/medium/high/xhigh/none）
        if self.provider == "sensetime":
            self._sanitize_reasoning_effort(kwargs=kwargs)
        # 🔒 安全校验：确保所有 tools 的 schema 合法（防止 type: null 等 400 错误）
        if "tools" in kwargs:
            kwargs["tools"] = self._sanitize_tools(kwargs["tools"])

        # 🔒 过滤空 system 消息（Kimi/Moonshot 不允许空 system message）
        # 🔒 过滤空 assistant 消息（content 为空且无 tool_calls，否则 API 400: content or tool_calls must be set）
        if "messages" in kwargs:
            def _keep_message(m):
                role = m.get("role")
                content = m.get("content", "") or ""
                if role == "system":
                    return bool(content.strip())
                if role == "assistant":
                    has_tool_calls = bool(m.get("tool_calls"))
                    return bool(content.strip()) or has_tool_calls
                return True
            kwargs["messages"] = [m for m in kwargs["messages"] if _keep_message(m)]
            # 🔧 双向修复孤儿 tool 消息（assistant.tool_calls ↔ role=tool 配对），
            #    防止历史被截断 / 任务中止后残留孤儿导致 API 400。
            #    这里是所有 LLM 调用的最终兜底（Agent 循环内已先修一次）。
            from .message_guard import sanitize_tool_messages
            kwargs["messages"] = sanitize_tool_messages(kwargs["messages"], label="model_manager")

        return self._chat_with_retry(client, **kwargs)

    def _trial_chat(self, **kwargs) -> dict:
        """
        试用模式下的 AI 调用 — 通过 7tan.com 服务端代理转发 DeepSeek。

        不重试（trial.php 服务端已做网络处理），失败直接 raise。
        """
        from ..security.auth_client import trial_call

        # 🔧 试用通道同样需要双向修复孤儿 tool 消息（与 chat() 兜底一致）
        from .message_guard import sanitize_tool_messages
        messages = sanitize_tool_messages(kwargs.get("messages", []), label="trial")
        model = kwargs.get("model", self.model_name)
        result = trial_call(self._trial_token, model, messages)

        if not result.get("success"):
            error_msg = result.get("error", "AI 试用调用失败")
            trials_left = result.get("trials_left", -1)
            if trials_left == 0:
                # 同步本地状态：试用次数已用完
                self._update_local_trial_count(0)
            raise RuntimeError(error_msg)

        # 同步本地试用次数
        new_count = result.get("trials_left", -1)
        if new_count >= 0:
            self._update_local_trial_count(new_count)

        # 将 trial.php 返回的数据包装为 OpenAI 兼容格式
        data = result
        choices = []
        for c in data.get("choices", []):
            msg = c.get("message", {})
            choices.append(type('Choice', (), {
                'message': type('Message', (), {
                    'content': msg.get('content', ''),
                    'role': msg.get('role', 'assistant'),
                    'tool_calls': msg.get('tool_calls'),
                })(),
                'finish_reason': c.get('finish_reason', 'stop'),
                'index': c.get('index', 0),
            })())
        usage_data = data.get("usage", {}) or {}
        response = type('Response', (), {
            'choices': choices,
            'usage': type('Usage', (), {
                'prompt_tokens': usage_data.get('prompt_tokens', 0),
                'completion_tokens': usage_data.get('completion_tokens', 0),
                'total_tokens': usage_data.get('total_tokens', 0),
            })(),
            'model': data.get('model', model),
        })()
        return response

    def _update_local_trial_count(self, new_count: int):
        """更新本地 Token 存储的试用次数（与服务端同步）"""
        try:
            from ..security.token_store import load_token, save_token
            token_data = load_token()
            if token_data:
                save_token(
                    token=token_data.get("token", ""),
                    username=token_data.get("username", ""),
                    level=token_data.get("level", "free"),
                    pro_expires=token_data.get("pro_expires", 0),
                    expires_in=token_data.get("expires_in", 2592000),
                    trial_ai_count=new_count,
                )
                logger.info(f"🎫 试用次数已同步: {new_count}")
        except Exception as e:
            logger.warning(f"同步试用次数失败: {e}")

    def _sanitize_surrogates(self, obj):
        """递归清理对象中的所有字符串，处理代理字符（surrogates）

        Python UTF-8 编码器不允许代理对字符（如 \ud83d）。
        这些通常来自损坏的 emoji 或不当的 UTF-16→UTF-8 转换。
        在发送给 API 前必须清理，否则 openai 库序列化 JSON 时会崩溃。

        有效代理对 → 实际 Unicode 字符，孤立代理 → '?'。
        支持 dict/list/tuple/set 等嵌套类型。
        """
        if isinstance(obj, str):
            return _fix_surrogates(obj)
        elif isinstance(obj, dict):
            return {self._sanitize_surrogates(k): self._sanitize_surrogates(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_surrogates(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._sanitize_surrogates(item) for item in obj)
        elif isinstance(obj, set):
            return {self._sanitize_surrogates(item) for item in obj}
        return obj

    @staticmethod
    def _safe_str(obj) -> str:
        """安全转为字符串，移除代理字符，防止日志崩溃"""
        try:
            s = str(obj)
            return _fix_surrogates(s)
        except Exception:
            return "<无法序列化的错误对象>"

    def _chat_with_retry(self, client, **kwargs):
        """带智能重试的 chat 调用（重试统一走 utils/retry.py 装饰器）"""
        # Clean surrogate chars before API call
        kwargs = self._sanitize_surrogates(kwargs)
        try:
            return self._chat_once(client, **kwargs)
        except Exception as e:
            # 2026-08-14 增强：连接类错误重试耗尽后，自动做一次快速网络诊断，
            # 把干巴巴的 "Connection error" 变成可操作的中文提示。
            is_conn_err = (
                isinstance(e, RetryExhausted)
                or "onnection" in type(e).__name__
                or "onnection" in str(e)
            )
            if is_conn_err:
                diag = self._diagnose_network()
                logger.error(f"🔌 AI 连接失败（已自动重试多次）: {diag}")
                if isinstance(e, RetryExhausted) and e.last_error is not None:
                    base = getattr(self, '_db_base_url', '') or 'AI 服务'
                    raise RuntimeError(
                        f"AI 服务连接失败（已自动重试多次仍无法连接）。\n诊断: {diag}\n"
                        f"建议：① 检查本机网络能否访问 {base}；"
                        f"② 稍等几分钟再试；③ 若持续失败，可在 设置→AI模型 中切换备用模型。"
                    ) from e.last_error
            raise

    def _diagnose_network(self) -> str:
        """快速诊断到 AI 服务的网络连通性（重试耗尽后调用一次）

        检查顺序：base_url 解析 → DNS 解析 → TCP 443 连通。
        返回人类可读的诊断结果，帮助区分"本机网络问题"与"AI 服务端问题"。
        """
        try:
            import socket
            from urllib.parse import urlparse
            base = getattr(self, '_db_base_url', '') or "https://api.deepseek.com/v1"
            host = urlparse(base).netloc.split(':')[0]
            if not host:
                return f"base_url 无效: {base}"
            # DNS 解析
            try:
                ips = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
                ip = ips[0][4][0]
            except Exception as dns_err:
                return f"DNS 解析失败: {host}（{dns_err}）"
            # TCP 443 连通性
            try:
                with socket.create_connection((host, 443), timeout=8):
                    return f"网络连通正常（{host}→{ip}:443 可达），问题可能在 AI 服务端或 API Key"
            except Exception as tcp_err:
                return f"无法连接 {host}（{ip}:443）: {tcp_err}"
        except Exception as e:
            return f"网络诊断失败: {e}"

    @retry(policy=_LLM_RETRY_CFG, auto_classify=False)
    def _chat_once(self, client, **kwargs):
        """单次 chat.completions.create 调用。
        由 @retry 统一处理：指数退避 + 抖动 + 错误分类（400 等不可重试错误直接抛出）。
        """
        return client.chat.completions.create(**kwargs)

    def _get_client(self):
        """懒加载创建 OpenAI 客户端（优先用数据库配置，回退 YAML）"""
        if self._client is not None:
            return self._client

        # 🔒 本地模型（provider 以 local_ 开头，如 local_7tan_model）不走 LLM API，也不走试用代理
        if str(getattr(self, 'provider', '')).startswith('local_'):
            raise RuntimeError("本地模型（7Tan）无需 API Key，请通过专用入口调用，勿走 LLM API/试用代理")

        from openai import OpenAI

        # 优先用数据库中的 api_key 和 base_url
        api_key = getattr(self, '_db_api_key', '')
        if isinstance(api_key, dict):
            api_key = api_key.get("key", "") or api_key.get("api_key", "") or ""
        api_key = str(api_key).strip() if api_key else ""
        base_url = getattr(self, '_db_base_url', '')
        if isinstance(base_url, dict):
            base_url = base_url.get("url", "") or base_url.get("base_url", "") or ""
        base_url = str(base_url).strip() if base_url else ""
        if not api_key:
            # 检查试用模式：如果用户已登录且还有 AI 试用次数，走服务端代理
            try:
                from ..security.token_store import load_token
                token_data = load_token()
                if token_data:
                    trial_token = token_data.get("token", "")
                    trials_left = token_data.get("trial_ai_count", 0)
                    if trial_token and trials_left > 0:
                        self._trial_mode = True
                        self._trial_token = trial_token
                        logger.info(
                            f"🎫 试用模式：通过 7tan.com 代理调用 AI（剩余 {trials_left} 次）"
                        )
                        return self  # 不创建真实 OpenAI client
            except Exception:
                pass

            raise RuntimeError(
                f"未配置 AI API Key！请在 设置→AI模型 中添加 {self.model_name} 的密钥"
            )

        import httpx
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1",
            timeout=httpx.Timeout(120.0, connect=30.0),
            max_retries=0,
        )
        logger.info(f"🤖 连接 AI [{self.model_name}]: provider={self.provider}, base_url={base_url}")
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
    # 解析 "auto" → 真实模型名
    if not model_name or model_name == "auto":
        try:
            from ..database.db import get_active_ai_config_raw
            cfg = get_active_ai_config_raw()
            model_name = cfg.get("model", "deepseek-flash") if cfg else "deepseek-flash"
        except Exception:
            model_name = "deepseek-flash"

    if model_name not in _model_cache:
        logger.debug(f"🤖 加载模型: {model_name}")
        _model_cache[model_name] = ModelManager(model_name)
    else:
        logger.debug(f"🤖 模型已缓存: {model_name}")
    return _model_cache[model_name]
def clear_model_cache():
    """清除模型缓存（配置变更后调用）"""
    _model_cache.clear()
def get_config() -> dict:
    """获取默认 LLM 配置（兼容旧代码调用）"""
    return {
        
        "temperature": 0.25,
        "max_tokens": 16384,
    }

