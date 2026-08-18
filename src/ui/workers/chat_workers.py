"""后台请求线程 — 从 chat_page 拆分"""

import json
import requests
from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal


API_BASE = "http://127.0.0.1:9800"


def _get_chat_timeout() -> int:
    """从配置读取客户端超时 = loop_timeout + 10"""
    try:
        from src.config.loader import load_config
        config = load_config()
        return config.get("agent", {}).get("loop_timeout", 600) + 10
    except Exception:
        return 610


class ChatWorker(QThread):
    """发送消息并接收回复，支持流式轮询"""

    finished = pyqtSignal(dict)
    streaming = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, message, session_id=None, model=None):
        super().__init__()
        self._message = message
        self._session_id = session_id
        self._model = model

    def run(self):
        logger.info("[ChatWorker] run start")
        try:
            data = {"message": self._message}
            if self._session_id:
                data["session_id"] = self._session_id
            if self._model:
                data["model"] = self._model

            resp = requests.post(f"{API_BASE}/api/chat/send", json=data, timeout=_get_chat_timeout())
            resp.raise_for_status()
            result = resp.json()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class StreamChatWorker(QThread):
    """SSE 流式读取 — 逐步 yield 思考过程 + 打字机效果"""

    event_received = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, message, session_id=None, model=None):
        super().__init__()
        self._message = message
        self._session_id = session_id
        self._model = model
        self._abort = False

    def run(self):
        try:
            data = {"message": self._message}
            if self._session_id:
                data["session_id"] = self._session_id
            if self._model:
                data["model"] = self._model

            with requests.post(
                f"{API_BASE}/api/chat/send/stream",
                json=data,
                stream=True,
                timeout=_get_chat_timeout(),
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
