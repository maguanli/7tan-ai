# -*- coding: utf-8 -*-
import sys, os
sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', buffering=1)

chat_page_path = 'D:/7tan/7tanAI/src/ui/chat_page.py'
with open(chat_page_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============ 1. Add StreamChatWorker after ChatWorker ============
old_worker = '''        except Exception as e:
            self.error.emit(str(e))


# ============================================================
#  消息气泡组件
# ============================================================
class MessageBubble'''

new_worker = '''        except Exception as e:
            self.error.emit(str(e))


# ============================================================
#  SSE 流式工作线程
# ============================================================
class StreamChatWorker(QThread):
    """SSE 流式读取 — 逐步 yield 思考过程 + 打字机效果"""
    event_received = pyqtSignal(dict)  # 每个 SSE 事件
    finished = pyqtSignal(dict)  # 最终结果
    error = pyqtSignal(str)

    def __init__(self, message, session_id=None, model=None):
        super().__init__()
        self._message = message
        self._session_id = session_id
        self._model = model
        self._abort = False

    def run(self):
        import requests as req
        try:
            data = {"message": self._message}
            if self._session_id:
                data["session_id"] = self._session_id
            if self._model:
                data["model"] = self._model

            with req.post(
                f"{API_BASE}/api/chat/send/stream",
                json=data,
                stream=True,
                timeout=600,
                headers={"Accept": "text/event-stream"}
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if self._abort:
                        break
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        event = json.loads(line[6:])
                        self.event_received.emit(event)
                        if event.get("type") == "done":
                            self.finished.emit(event)
                            return
                        if event.get("type") == "session_id":
                            self.finished.emit(event)
                            return
                        if event.get("type") == "error":
                            self.error.emit(event.get("message", "Unknown error"))
                            return
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.error.emit(str(e))

    def abort(self):
        """终止流式请求"""
        self._abort = True


# ============================================================
#  消息气泡组件
# ============================================================
class MessageBubble'''

content = content.replace(old_worker, new_worker)

# ============ 2. Modify _send_message to use streaming ============
old_send = '''    def _send_message(self, text: str = None):
        \"\"\"发送消息\"\"\"
        if text is None:
            text = self._input.toPlainText().strip()
        if not text:
            return

        self._input.clear()
        self._add_message("user", text)

        # 获取当前模型
        model = None
        idx = self._model_combo.currentIndex()
        if idx >= 0:
            model_key = self._model_combo.itemData(idx)
            if model_key:
                from ..config.loader import load_config
                cfg = load_config()
                model_cfg = cfg.get("ai", {}).get("configs", {}).get(model_key, {})
                model = model_cfg.get("model", model_key)

        # 显示等待动画
        thinking_msg = self._add_message("system", "⏳ AI 思考中...")

        # 启动工作线程
        self._worker = ChatWorker(text, self._current_session_id, model)
        self._worker.finished.connect(lambda d: self._on_response(d, thinking_msg))
        self._worker.error.connect(lambda e: self._on_error(e, thinking_msg))
        self._worker.start()

    def _on_response(self, data, thinking_msg=None):
        \"\"\"处理回复\"\"\"
        # 移除思考中的消息
        if thinking_msg:
            self._remove_message(thinking_msg)

        self._current_session_id = data.get("session_id", self._current_session_id)
        result = data.get("result", "无响应")
        cost = data.get("cost", 0)
        iterations = data.get("iterations", 0)
        success = data.get("success", False)

        if not success:
            self._add_message("error", f"❌ {result}", cost=cost, iterations=iterations)
        else:
            self._add_message("assistant", result, cost=cost, iterations=iterations,
                            session_id=self._current_session_id)

        # 刷新会话列表
        if self._current_session_id:
            QTimer.singleShot(500, self._refresh_sessions)

    def _on_error(self, error_msg: str, thinking_msg=None):
        \"\"\"处理错误\"\"\"
        if thinking_msg:
            self._remove_message(thinking_msg)
        self._add_message("error", f"❌ 请求失败: {error_msg}")'''

new_send = '''    def _send_message(self, text: str = None):
        \"\"\"发送消息（支持流式输出 + 思考过程展示）\"\"\"
        if text is None:
            text = self._input.toPlainText().strip()
        if not text:
            return

        self._input.clear()
        self._add_message("user", text)

        # 获取当前模型
        model = None
        idx = self._model_combo.currentIndex()
        if idx >= 0:
            model_key = self._model_combo.itemData(idx)
            if model_key:
                from ..config.loader import load_config
                cfg = load_config()
                model_cfg = cfg.get("ai", {}).get("configs", {}).get(model_key, {})
                model = model_cfg.get("model", model_key)

        # 尝试使用流式 SSE，失败时 fallback 到传统请求
        try:
            self._send_streaming(text, model)
        except Exception as e:
            logger.warning(f"流式请求失败，回退到传统模式: {e}")
            # 显示等待动画
            thinking_msg = self._add_message("system", "\\u23f3 AI \\u601d\\u8003\\u4e2d...")
            self._worker = ChatWorker(text, self._current_session_id, model)
            self._worker.finished.connect(lambda d: self._on_response(d, thinking_msg))
            self._worker.error.connect(lambda e: self._on_error(e, thinking_msg))
            self._worker.start()

    def _send_streaming(self, text: str, model: str = None):
        \"\"\"使用 SSE 流式发送消息，展示思考过程 + 打字机效果\"\"\"
        # 创建"思考中"状态栏（将在收到第一个事件后保留）
        self._streaming_assistant_bubble = None  # AI 回复气泡
        self._streaming_thinking_container = None  # 思考过程容器
        self._streaming_tool_calls = []  # 工具调用列表
        self._streaming_text = ""  # 累积文本
        self._streaming_session_id = self._current_session_id

        # 创建思考过程气泡
        self._streaming_thinking_bubble = self._add_message("system", "\\u23f3 AI \\u6b63\\u5728\\u601d\\u8003...")

        # 启动 SSE 流式线程
        self._stream_worker = StreamChatWorker(text, self._current_session_id, model)
        self._stream_worker.event_received.connect(self._on_stream_event)
        self._stream_worker.finished.connect(self._on_stream_finished)
        self._stream_worker.error.connect(lambda e: self._on_error(e, self._streaming_thinking_bubble))
        self._stream_worker.start()

    def _on_stream_event(self, event: dict):
        \"\"\"处理流式事件 — 实时更新思考过程和内容\"\"\"
        etype = event.get("type", "")

        if etype == "thinking":
            # 更新思考状态
            if self._streaming_thinking_bubble:
                msg = event.get("message", "")
                self._streaming_thinking_bubble.update_content(msg)

        elif etype == "iteration":
            # 显示迭代进度
            it = event.get("iteration", 1)
            total = event.get("max_iterations", 80)
            if self._streaming_thinking_bubble:
                self._streaming_thinking_bubble.update_content(f"\\ud83d\\udd04 \\u7b2c {it}/{total} \\u8f6e\\u63a8\\u7406...")

        elif etype == "tool_call":
            # 实时显示工具调用
            tool_name = event.get("tool_name", "unknown")
            args = event.get("args", {})
            tc = {"tool": tool_name, "args": args, "status": "running"}
            self._streaming_tool_calls.append(tc)
            self._update_streaming_display()

        elif etype == "tool_result":
            # 更新工具调用状态
            tool_name = event.get("tool_name", "")
            is_error = event.get("error", False)
            summary = event.get("summary", "")
            for tc in self._streaming_tool_calls:
                if tc.get("tool") == tool_name and tc.get("status") == "running":
                    tc["status"] = "failed" if is_error else "success"
                    tc["summary"] = summary
            self._update_streaming_display()

        elif etype == "text_chunk":
            # 打字机效果 — 逐段追加文本
            chunk = event.get("content", "")
            self._streaming_text += chunk
            if self._streaming_assistant_bubble is None:
                # 第一个文本块到达，创建 AI 回复气泡（带工具调用）
                self._streaming_assistant_bubble = self._add_message(
                    "assistant", self._streaming_text,
                    is_streaming=True,
                    tool_calls=self._streaming_tool_calls,
                    session_id=self._streaming_session_id,
                )
            else:
                self._streaming_assistant_bubble.update_content(
                    self._streaming_text, is_streaming=True
                )
            # 滚动到底部
            self._scroll_to_bottom()

        elif etype == "cost":
            # 费用更新（最终会在 done 中设置）
            pass

        elif etype == "session_id":
            self._streaming_session_id = event.get("session_id", self._streaming_session_id)
            self._current_session_id = self._streaming_session_id

    def _update_streaming_display(self):
        \"\"\"更新当前展示的工具调用步骤\"\"\"
        # 如果已经有了 assistant 气泡，更新它的 tool_calls
        if self._streaming_assistant_bubble and hasattr(self._streaming_assistant_bubble, '_tool_calls'):
            pass  # 气泡已创建时携带了工具调用

        # 如果还没有 assistant 气泡，但在思考过程中有工具调用
        # 那就更新 thinking 气泡显示工具调用信息
        if self._streaming_thinking_bubble and self._streaming_tool_calls:
            active_tools = [t for t in self._streaming_tool_calls if t.get("status") == "running"]
            if active_tools:
                names = ", ".join([t["tool"] for t in active_tools])
                self._streaming_thinking_bubble.update_content(
                    f"\\ud83d\\udd04 \\u6b63\\u5728\\u8c03\\u7528\\u5de5\\u5177: {names}"
                )

    def _on_stream_finished(self, data: dict):
        \"\"\"流式响应完成\"\"\"
        # 移除 thinking 气泡
        if self._streaming_thinking_bubble:
            self._remove_message(self._streaming_thinking_bubble)
            self._streaming_thinking_bubble = None

        success = data.get("success", True)
        result = data.get("result", self._streaming_text)
        cost = data.get("cost", 0)
        iterations = data.get("iterations", 0)
        session_id = data.get("session_id", self._streaming_session_id)

        if session_id:
            self._current_session_id = session_id

        if not success:
            self._add_message("error", result, cost=cost, iterations=iterations)
        elif self._streaming_assistant_bubble:
            # 更新最终状态（去掉流式标记、更新费用）
            self._streaming_assistant_bubble._is_streaming = False
            self._streaming_assistant_bubble.update_content(result, is_streaming=False)
            # 更新 tool_calls 最终状态
            if self._streaming_tool_calls:
                # 清除未完成的 running 状态
                for tc in self._streaming_tool_calls:
                    if tc.get("status") == "running":
                        tc["status"] = "failed"
            self._streaming_assistant_bubble = None

        # 刷新会话列表
        if self._current_session_id:
            QTimer.singleShot(500, self._refresh_sessions)

    def _on_response(self, data, thinking_msg=None):
        \"\"\"处理回复（传统模式 fallback）\"\"\"
        # 移除思考中的消息
        if thinking_msg:
            self._remove_message(thinking_msg)

        self._current_session_id = data.get("session_id", self._current_session_id)
        result = data.get("result", "\\u65e0\\u54cd\\u5e94")
        cost = data.get("cost", 0)
        iterations = data.get("iterations", 0)
        success = data.get("success", False)

        if not success:
            self._add_message("error", f"\\u274c {result}", cost=cost, iterations=iterations)
        else:
            self._add_message("assistant", result, cost=cost, iterations=iterations,
                            session_id=self._current_session_id)

        # 刷新会话列表
        if self._current_session_id:
            QTimer.singleShot(500, self._refresh_sessions)

    def _on_error(self, error_msg: str, thinking_msg=None):
        \"\"\"处理错误\"\"\"
        if thinking_msg:
            self._remove_message(thinking_msg)
        self._add_message("error", f"\\u274c \\u8bf7\\u6c42\\u5931\\u8d25: {error_msg}")'''

content = content.replace(old_send, new_send)

with open(chat_page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Chat page streaming support added successfully')
print(f'File size: {len(content)} chars')
