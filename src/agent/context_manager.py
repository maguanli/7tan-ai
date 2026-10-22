"""
上下文管理器 — 对话历史、token 管理、窗口截断
"""
from loguru import logger


class ContextManager:
    """管理 Agent 对话上下文"""

    def __init__(self, task: str = "", session_id: str = None,
                 max_messages: int = 50, max_tokens_estimate: int = 32000,
                 max_message_chars: int = 24000):
        self.task = task
        self.session_id = session_id
        self.max_messages = max_messages
        self.max_tokens_estimate = max_tokens_estimate
        # 🔒 2026-10-23 单条消息体积上限：历史里可能存在超长消息
        #    （如某次把记忆库数万段经历整篇吐进一条 assistant 消息，长度 9.3MB），
        #    只按「条数」截断会让整条超大消息原样发给 API →
        #    400 maximum context length（请求 436 万 tokens > 上限 104 万），AI 全程不可用。
        self.max_message_chars = max_message_chars
        self.history = []
        self._total_tokens = 0

        # 🔥 加载会话历史（AI 现在能记住之前的对话了）
        if self.session_id:
            try:
                from .conversation import get_session_messages
                db_msgs = get_session_messages(self.session_id, limit=self.max_messages)
                for m in db_msgs:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    if role in ("user", "assistant", "system"):
                        # 跳过空 assistant 消息（content 为空会导致 API 400: content or tool_calls must be set）
                        if role == "assistant" and not (content or "").strip():
                            continue
                        content = self._cap(content)
                        self.history.append({"role": role, "content": content})
                        self._total_tokens += len(content) // 2
                # 🔒 加载后立即按「体积」做一次预算裁剪（原来只在 add_* 时检查，
                #    纯加载路径（如 WEB 对话直接复用 ctx 历史）完全绕过了裁剪）
                self._enforce_budget()
                if self.history:
                    logger.info(f"📚 加载会话历史: {len(self.history)} 条消息")
            except Exception as e:
                logger.warning(f"⚠️ 加载会话历史失败: {e}")

    def add_user_message(self, content: str):
        """添加用户消息"""
        content = self._cap(content)
        self.history.append({"role": "user", "content": content})
        self._total_tokens += len(content) // 2  # 粗略估算
        self._trim_if_needed()

    def add_assistant_message(self, content: str):
        """添加助手消息"""
        content = self._cap(content)
        self.history.append({"role": "assistant", "content": content})
        self._total_tokens += len(content) // 2
        self._trim_if_needed()

    def add_tool_result(self, tool_call_id: str, content: str):
        """添加工具调用结果"""
        wrapped = f"[TOOL_RESULT]\n{content[:self.max_message_chars]}\n[/TOOL_RESULT]"
        self.history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": wrapped,  # 硬保护，极高上限
        })
        self._total_tokens += len(content) // 2
        self._trim_if_needed()

    def _cap(self, content: str) -> str:
        """单条消息体积硬保护（2026-10-23）：超长正文保留头 60% + 尾 40%。"""
        try:
            text = content if isinstance(content, str) else str(content or "")
        except Exception:
            return ""
        limit = int(self.max_message_chars or 0)
        if limit <= 0 or len(text) <= limit:
            return text
        marker = f"\n\n…[消息过长，已截断 {len(text) - limit} 字符]…\n\n"
        head = int(limit * 0.6)
        tail = max(0, limit - head - len(marker))
        logger.warning(f"✂️ 单条消息超长（{len(text)} 字符）→ 截断至 {limit} 字符")
        return text[:head] + marker + (text[-tail:] if tail else "")

    def _enforce_budget(self):
        """按「体积」执行预算（2026-10-23）：单条硬截断 → 摘要 → 丢弃最旧消息。

        三道闸缺一不可：
          ① 单条硬截断——超长消息（如 9MB 的输出）即使只有一条也会撑爆上下文；
          ② 摘要——条数多但每条不大时，摘要比丢弃更保信息；
          ③ 丢弃——摘要后仍超限（或条数太少无法摘要）时，从最旧开始丢。
        """
        # ① 单条体积硬保护（防御外部直接写 history 绕过 _cap）
        for m in self.history:
            c = m.get("content") or ""
            if isinstance(c, str) and len(c) > self.max_message_chars:
                m["content"] = self._cap(c)

        self._total_tokens = sum(len(m.get("content") or "") // 2 for m in self.history)
        if self._total_tokens <= self.max_tokens_estimate:
            return

        # ② 摘要压缩
        if len(self.history) >= 10:
            try:
                self.summarize()
            except Exception as e:
                logger.warning(f"⚠️ 上下文摘要失败: {e}")

        # ③ 从最旧开始丢弃（至少保留最后一条，即当前任务）
        dropped = 0
        while self._total_tokens > self.max_tokens_estimate and len(self.history) > 1:
            self.history.pop(0)
            dropped += 1
            self._total_tokens = sum(len(m.get("content") or "") // 2 for m in self.history)
        if dropped:
            logger.warning(
                f"✂️ 上下文超预算，丢弃最旧 {dropped} 条消息"
                f"（剩余 {len(self.history)} 条，估算 {self._total_tokens} tokens）"
            )

    def get_messages(self) -> list:
        """获取当前消息历史"""
        return self.history

    def clear(self):
        """清空上下文"""
        self.history = []
        self._total_tokens = 0

    def summarize(self, model=None) -> str:
        """
        压缩上下文：调用 LLM 对历史进行摘要
        当提供了 model 时，使用 AI 摘要；否则使用规则压缩
        """
        if len(self.history) < 10:
            return ""

        # 保留最近若干条消息（以 60% 预算为限，避免把超大消息当"最近"留下）
        _budget = int(self.max_tokens_estimate * 0.6)
        recent_messages = []
        _used = 0
        for _m in reversed(self.history):
            _t = len(_m.get("content") or "") // 2
            if recent_messages and _used + _t > _budget:
                break
            recent_messages.append({"role": _m.get("role", "user"), "content": self._cap(_m.get("content") or "")})
            _used += _t
        recent_messages.reverse()
        old_messages = self.history[: len(self.history) - len(recent_messages)] if recent_messages else list(self.history)

        if model:
            # AI 摘要模式
            summary = self._ai_summarize(old_messages, model)
        else:
            # 规则压缩（fallback）
            summary = self._rule_summarize(old_messages)

        # 重建上下文
        self.history = [
            {"role": "system", "content": "对话历史摘要:\n" + summary},
        ] + recent_messages

        self._total_tokens = sum(len(m.get("content", "")) // 2 for m in self.history)
        return summary

    def _rule_summarize(self, messages: list) -> str:
        """简单规则压缩：取每轮对话的关键信息"""
        summary_parts = []
        for msg in messages:
            content = msg.get("content", "")
            if content and msg.get("role") in ("user", "assistant"):
                # 取每条消息的前 120 字符
                summary_parts.append(content[:120] + ("..." if len(content) > 120 else ""))
        return "; ".join(summary_parts[-10:]) if summary_parts else "无关键对话"

    def _ai_summarize(self, messages: list, model_name: str = None) -> str:
        """
        使用 AI 对对话历史进行摘要
        调用 OpenAI 兼容 API
        """
        try:
            from ..agent.model_manager import ModelManager

            # 构建摘要请求
            conversation_text = ""
            for msg in messages[-20:]:  # 最多取最近 20 条
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content:
                    conversation_text += f"[{role}]: {content[:200]}\n"

            # 使用 ModelManager 统一的 API 调用（从数据库获取模型名）
            from ..config.loader import get_active_ai_config
            if not model_name:
                ai_cfg = get_active_ai_config()
                model_name = ai_cfg.get("model", "")

            mm = ModelManager(model_name)
            response = mm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个对话摘要助手。请用 2-4 句话简洁摘要以下对话的关键内容和决策，保留任务目标和重要结论。",
                    },
                    {
                        "role": "user",
                        "content": f"请摘要以下对话记录:\n\n{conversation_text}",
                    },
                ],
                max_tokens=300,
            )

            summary = response.choices[0].message.content.strip()
            logger.debug(f"📝 AI 摘要 ({len(summary)} 字符)")
            return summary

        except Exception as e:
            logger.warning(f"⚠️ AI 摘要失败，fallback 到规则压缩: {e}")
            return self._rule_summarize(messages)

    def _trim_if_needed(self):
        """按消息数量截断（在安全边界处切，避免产生孤儿 tool 消息）"""
        if len(self.history) > self.max_messages:
            cut = len(self.history) - self.max_messages
            # 🔧 安全边界：切口不得落在 tool 响应中间。
            #    self.history[-N:] 可能切掉了声明 tool_calls 的 assistant，
            #    却把 role=tool 的响应留在窗口内 → 下次请求 API 400:
            #    "Messages with role 'tool' must be a response to a preceding
            #     message with 'tool_calls'"。
            #    若 history[cut] 仍是 tool 响应，向后顺延到第一条非 tool 消息。
            _shift = 0
            while cut < len(self.history) and self.history[cut].get("role") == "tool":
                cut += 1
                _shift += 1
            self.history = self.history[cut:]
            logger.debug(
                f"📎 截断后保留 {len(self.history)} 条消息"
                + (f"（安全边界顺延 {_shift} 条，避免孤儿 tool 响应）" if _shift else "")
            )

        if self._total_tokens > self.max_tokens_estimate:
            logger.debug(f"📎 Token 估算 {self._total_tokens} > {self.max_tokens_estimate}")
            self._enforce_budget()
    def __len__(self):
        return len(self.history)


def should_compress_context(token_count: int, limit: int = 50_000) -> bool:
    """是否需要压缩上下文"""
    return token_count > limit


def compress_context(ctx: ContextManager, model=None) -> str:
    """压缩上下文，返回摘要"""
    return ctx.summarize(model=model)


# 别名
ConversationContext = ContextManager
