"""
WebSocket 管理器 — 连接管理 + 消息广播 + 确认机制
详见架构文档 §21.6
"""
import asyncio
import json
import uuid
from typing import Any, Callable, Optional

from fastapi import WebSocket
from loguru import logger


class WebSocketManager:
    """
    WebSocket 连接管理器

    功能:
    - 多客户端连接管理
    - 按类型广播消息
    - 进度推送
    - 用户确认请求/响应 (§12.2)
    """

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._pending_confirms: dict[str, asyncio.Future] = {}
        self._message_handlers: dict[str, Callable] = {}

    # ===== 连接管理 =====

    async def connect(self, ws: WebSocket):
        """接受并注册新连接"""
        await ws.accept()
        client_id = str(uuid.uuid4())[:8]
        self._connections[client_id] = ws
        logger.info(f"🔌 WebSocket 连接: {client_id}")
        return client_id

    def disconnect(self, client_id: str):
        """断开连接"""
        self._connections.pop(client_id, None)
        logger.info(f"🔌 WebSocket 断开: {client_id}")

    def get_connection(self, client_id: str) -> Optional[WebSocket]:
        """获取连接"""
        return self._connections.get(client_id)

    @property
    def active_count(self) -> int:
        return len(self._connections)

    # ===== 消息发送 =====

    async def send_to(self, client_id: str, data: dict):
        """发送消息给指定客户端"""
        ws = self._connections.get(client_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"发送消息失败 {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, data: dict):
        """广播消息给所有客户端"""
        disconnected = []
        for client_id, ws in self._connections.items():
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect(cid)

    # ===== 类型化消息 =====

    async def send_progress(self, data: dict):
        """推送任务进度 — §21.6 task_progress"""
        await self.broadcast({
            "type": "task_progress",
            "data": data,
        })

    async def send_log(self, level: str, message: str):
        """推送日志 — §21.6 log"""
        from datetime import datetime
        await self.broadcast({
            "type": "log",
            "data": {
                "level": level,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        })

    async def send_ai_message(self, content: str, is_streaming: bool = False):
        """推送 AI 消息 — §21.6 ai_message"""
        await self.broadcast({
            "type": "ai_message",
            "data": {
                "content": content,
                "is_streaming": is_streaming,
            },
        })

    async def send_health(self, data: dict):
        """推送系统健康状态 — §21.6 health"""
        await self.broadcast({
            "type": "health",
            "data": data,
        })

    async def send_confirm_request(self, file_path: str, diff: str,
                                   backup: str, timeout: int = 60) -> bool:
        """
        发送用户确认请求 — §12.2
        返回 True=确认, False=取消/超时
        """
        confirm_id = str(uuid.uuid4())[:8]

        # 创建 Future 等待用户响应
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_confirms[confirm_id] = future

        # 广播确认请求
        await self.broadcast({
            "type": "confirm_modify",
            "data": {
                "confirm_id": confirm_id,
                "file": file_path,
                "diff": diff,
                "backup": backup,
            },
        })

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"确认超时: {file_path}")
            return False
        finally:
            self._pending_confirms.pop(confirm_id, None)

    def resolve_confirm(self, confirm_id: str, accepted: bool):
        """处理用户确认响应"""
        future = self._pending_confirms.get(confirm_id)
        if future and not future.done():
            future.set_result(accepted)

    # ===== 消息处理 =====

    def on_message(self, msg_type: str):
        """消息处理器装饰器（预留）"""
        def decorator(func):
            self._message_handlers[msg_type] = func
            return func
        return decorator

    async def handle_message(self, client_id: str, data: dict):
        """处理收到的消息"""
        msg_type = data.get("type", "")

        # 处理确认响应
        if msg_type == "confirm_response":
            confirm_id = data.get("confirm_id", "")
            accepted = data.get("accepted", False)
            self.resolve_confirm(confirm_id, accepted)
            return

        # 调用注册的处理器
        handler = self._message_handlers.get(msg_type)
        if handler:
            await handler(client_id, data)


# 全局 WebSocket 管理器实例
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """获取全局 WebSocket 管理器单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
