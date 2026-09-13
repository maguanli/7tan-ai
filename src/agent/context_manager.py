"""
上下文管理器 — 对话历史、token 管理、窗口截断
"""
from loguru import logger


class ContextManager:
    """管理 Agent 对话上下文"""

    def __init__(self, task: str = "", session_id: str = None,
                 max_messages: int = 50, max_tokens_estimate: int = 32000):
        self.task = task
        self.session_id = session_id
        self.max_messages = max_messages
        self.max_tokens_estimate = max_tokens_estimate
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
                        self.history.append({"role": role, "content": content})
                        self._total_tokens += len(content) // 2
                if self.history:
                    logger.info(f"📚 加载会话历史: {len(self.history)} 条消息")
            except Exception as e:
                logger.warning(f"⚠️ 加载会话历史失败: {e}")

    def add_user_message(self, content: str):
        """添加用户消息"""
        self.history.append({"role": "user", "content": content})
        self._total_tokens += len(content) // 2  # 粗略估算
        self._trim_if_needed()

    def add_assistant_message(self, content: str):
        """添加助手消息"""
        self.history.append({"role": "assistant", "content": content})
        self._total_tokens += len(content) // 2
        self._trim_if_needed()

    def add_tool_result(self, tool_call_id: str, content: str):
        """添加工具调用结果"""
        wrapped = f"[TOOL_RESULT]\n{content[:100000]}\n[/TOOL_RESULT]"
        self.history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": wrapped,  # 硬保护，极高上限
        })
        self._total_tokens += len(content) // 2
        self._trim_if_needed()

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

        # 保留最近 5 条消息
        old_messages = self.history[:-5]
        recent_messages = self.history[-5:]

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
            self.summarize()
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
