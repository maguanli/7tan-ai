"""
QQ 桥接插件 — 通过 OneBot WebSocket 协议连接 QQ
支持：正向 WebSocket 连接、收发群消息/私聊消息
"""

import json
import time
import queue
import threading
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("qq_bridge")

# ========== 全局状态 ==========
_ws_client = None
_recv_thread = None
_message_queue = queue.Queue()
_connected = False
_config = {}
_should_stop = False

# ========== 配置 ==========
DEFAULT_CONFIG = {
    "ws_url": "ws://127.0.0.1:3001",       # OneBot 正向 WS 地址
    "access_token": "",                      # 鉴权 token（可选）
    "auto_reconnect": True,
    "reconnect_interval": 5,
    "max_queue_size": 200,
}


def _load_config():
    """从配置文件加载 QQ 桥接配置"""
    global _config
    try:
        cfg_path = Path(__file__).parent / "config.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                _config = {**DEFAULT_CONFIG, **json.load(f)}
        else:
            _config = DEFAULT_CONFIG.copy()
            _save_config()
    except Exception:
        _config = DEFAULT_CONFIG.copy()


def _save_config():
    try:
        cfg_path = Path(__file__).parent / "config.json"
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(_config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存配置失败: {e}")


def _ws_recv_loop():
    """WebSocket 接收线程"""
    global _connected, _ws_client, _should_stop
    logger.info("WebSocket 接收线程启动")

    while not _should_stop:
        try:
            from websocket import create_connection, WebSocketConnectionClosedException
        except ImportError:
            logger.error("缺少 websocket-client 库，请 pip install websocket-client")
            time.sleep(10)
            continue

        try:
            ws_url = _config.get("ws_url", "ws://127.0.0.1:3001")
            access_token = _config.get("access_token", "")

            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            _ws_client = create_connection(ws_url, header=headers, timeout=10)
            _connected = True
            logger.info(f"已连接到 OneBot: {ws_url}")

            while not _should_stop:
                try:
                    _ws_client.settimeout(1.0)
                    raw = _ws_client.recv()
                    if raw:
                        _handle_raw_message(raw)
                except Exception:
                    if _should_stop:
                        break
                    try:
                        _ws_client.ping()
                    except Exception:
                        logger.warning("WebSocket 连接断开")
                        break

        except Exception as e:
            _connected = False
            logger.warning(f"WebSocket 连接失败: {e}")
            if _should_stop:
                break
            if _config.get("auto_reconnect", True):
                interval = _config.get("reconnect_interval", 5)
                logger.info(f"{interval} 秒后重连...")
                time.sleep(interval)

    _connected = False
    logger.info("WebSocket 接收线程退出")


def _handle_raw_message(raw: str):
    """处理原始 WebSocket 消息"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    post_type = data.get("post_type", "")
    if post_type == "message":
        msg_type = data.get("message_type", "")
        user_id = data.get("user_id", 0)
        raw_message = data.get("raw_message", "")
        message_id = data.get("message_id", 0)

        msg_obj = {
            "type": msg_type,
            "user_id": user_id,
            "nickname": data.get("sender", {}).get("nickname", ""),
            "message": raw_message,
            "message_id": message_id,
            "group_id": data.get("group_id", 0) if msg_type == "group" else 0,
            "time": datetime.now().isoformat(),
            "raw": data,
        }

        if _message_queue.qsize() < _config.get("max_queue_size", 200):
            _message_queue.put(msg_obj)
        else:
            try:
                _message_queue.get_nowait()
                _message_queue.put(msg_obj)
            except queue.Empty:
                _message_queue.put(msg_obj)

        logger.debug(f"收到消息: [{msg_type}] {user_id}: {raw_message[:50]}")

    elif post_type == "meta_event":
        logger.debug(f"元事件: {data.get('meta_event_type', '')}")
    elif post_type == "notice":
        logger.debug(f"通知: {data.get('notice_type', '')}")


# ========== 工具函数 ==========

@register_tool(
    name="qq_connect",
    description="连接到 QQ（OneBot WebSocket）。使用前确保 OneBot 服务（如 go-cqhttp、NapCat）已启动。",
    parameters={
        "ws_url": {"type": "string", "description": "OneBot WS 地址，默认 ws://127.0.0.1:3001", "default": "ws://127.0.0.1:3001"},
        "access_token": {"type": "string", "description": "鉴权 token（可选）", "default": ""},
    }
)
def qq_connect(ws_url: str = "ws://127.0.0.1:3001", access_token: str = "") -> str:
    """连接 QQ"""
    global _config, _recv_thread, _should_stop

    _load_config()
    _config["ws_url"] = ws_url
    if access_token:
        _config["access_token"] = access_token
    _save_config()

    if _recv_thread and _recv_thread.is_alive():
        qq_disconnect()

    _should_stop = False
    _recv_thread = threading.Thread(target=_ws_recv_loop, daemon=True, name="QQ-Bridge-Recv")
    _recv_thread.start()

    for i in range(30):
        time.sleep(0.1)
        if _connected:
            return f"已成功连接到 QQ！(OneBot: {ws_url})"

    return f"正在连接中... 如果长时间未连上请检查 OneBot 是否已启动"


@register_tool(
    name="qq_disconnect",
    description="断开 QQ 连接",
    parameters={}
)
def qq_disconnect() -> str:
    """断开连接"""
    global _should_stop, _connected, _ws_client
    _should_stop = True

    if _ws_client:
        try:
            _ws_client.close()
        except Exception:
            pass
        _ws_client = None

    _connected = False
    return "已断开 QQ 连接"


@register_tool(
    name="qq_send_message",
    description="发送 QQ 消息。支持群聊和私聊。",
    parameters={
        "target_id": {"type": "integer", "description": "目标 ID：群号（群聊）或 QQ 号（私聊）"},
        "message": {"type": "string", "description": "要发送的消息内容"},
        "msg_type": {"type": "string", "description": "消息类型：group（群聊）或 private（私聊）", "default": "group"},
    }
)
def qq_send_message(target_id: int, message: str, msg_type: str = "group") -> str:
    """发送 QQ 消息"""
    global _ws_client, _connected

    if not _connected or not _ws_client:
        return "未连接到 QQ，请先调用 qq_connect"

    try:
        if msg_type == "group":
            payload = {
                "action": "send_group_msg",
                "params": {
                    "group_id": target_id,
                    "message": message,
                }
            }
        else:
            payload = {
                "action": "send_private_msg",
                "params": {
                    "user_id": target_id,
                    "message": message,
                }
            }

        _ws_client.send(json.dumps(payload, ensure_ascii=False))
        return f"消息已发送 ({msg_type} -> {target_id})"

    except Exception as e:
        _connected = False
        return f"发送失败: {e}"


@register_tool(
    name="qq_get_messages",
    description="获取收到的 QQ 消息队列（不清空）。用于查看有没有新消息。",
    parameters={
        "max_count": {"type": "integer", "description": "最多返回多少条", "default": 10},
        "clear": {"type": "boolean", "description": "读取后是否清空队列", "default": False},
    }
)
def qq_get_messages(max_count: int = 10, clear: bool = False) -> str:
    """读取消息队列"""
    messages = []
    try:
        while len(messages) < max_count:
            msg = _message_queue.get_nowait()
            messages.append(msg)
    except queue.Empty:
        pass

    if not messages:
        status = "已连接" if _connected else "未连接"
        return f"暂无新消息 (QQ状态: {status})"

    lines = [f"收到 {len(messages)} 条消息:"]
    for i, msg in enumerate(messages, 1):
        nickname = msg.get("nickname", "")
        user_id = msg.get("user_id", "")
        text = msg.get("message", "")[:100]
        gid = msg.get("group_id", 0)
        mtype = "群" if msg["type"] == "group" else "私"

        if gid:
            lines.append(f"  [{i}] [{mtype}聊|群{gid}] {nickname}({user_id}): {text}")
        else:
            lines.append(f"  [{i}] [{mtype}聊] {nickname}({user_id}): {text}")

    if clear:
        pass

    return "\n".join(lines)


@register_tool(
    name="qq_status",
    description="查看 QQ 连接状态",
    parameters={}
)
def qq_status() -> str:
    """查看状态"""
    status = "已连接" if _connected else "未连接"
    lines = [
        f"QQ 桥接状态: {status}",
        f"OneBot 地址: {_config.get('ws_url', '未配置')}",
        f"消息队列: {_message_queue.qsize()} 条待处理",
        f"自动重连: {'开启' if _config.get('auto_reconnect') else '关闭'}",
    ]
    return "\n".join(lines)


_load_config()
logger.info("QQ 桥接插件已加载")
