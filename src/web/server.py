"""
后端 API 服务器 — FastAPI + WebSocket + REST API
纯 API 模式，桌面版使用 PyQt6 原生控件
"""
import sys
import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from loguru import logger

# API 安全：仅允许本地请求（桌面应用）或带 token 的远程请求
import os
import secrets


def _load_or_create_api_token() -> str:
    """加载或自动生成 API Token（优先级：环境变量 > data/.api_token > 随机生成并持久化）。

    防止未配置 7TAN_API_TOKEN 时 API 完全无鉴权（远程/本地进程均可驱动 agent）。
    """
    env_token = os.environ.get("7TAN_API_TOKEN", "").strip()
    if env_token:
        return env_token
    token_file = Path(__file__).resolve().parent.parent.parent / "data" / ".api_token"
    try:
        if token_file.exists():
            t = token_file.read_text(encoding="utf-8").strip()
            if t:
                return t
    except Exception:
        pass
    token = secrets.token_urlsafe(32)
    try:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(token, encoding="utf-8")
        logger.info(f"🔑 已自动生成 API Token 并保存至 {token_file}")
    except Exception as e:
        logger.warning(f"API Token 持久化失败: {e}")
    return token


API_TOKEN = _load_or_create_api_token()

# 全局服务器 socket 引用，供 shutdown_server() 使用
_server_socket = None


def _get_project_root():
    """获取项目根目录 — 兼容开发模式和 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


PROJECT_ROOT = _get_project_root()

# 确保 src 目录在 path 中
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.config.version import APP_VERSION as _APP_VERSION
except Exception:
    _APP_VERSION = "1.0.0"

app = FastAPI(title="7Tan", version=_APP_VERSION, docs_url=None, redoc_url=None)


# ===== API 安全中间件 =====
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """简单认证：本地请求放行，远程请求需要 token"""
    host = request.client.host if request.client else ""
    path = request.url.path

    # 健康检查、WebSocket、静态页面（网页版前端）放行；仅 /api/* 需鉴权
    if path == "/api/health" or path.startswith("/ws") or not path.startswith("/api/"):
        return await call_next(request)

    # 本地请求放行
    if host in ("127.0.0.1", "::1", "localhost"):
        return await call_next(request)

    # 远程请求需要 API Token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if API_TOKEN and token == API_TOKEN:
        return await call_next(request)

    logger.warning(f"未授权的远程请求: {host} -> {path}")
    return JSONResponse({"error": "unauthorized"}, status_code=401)

# ===== WebSocket 管理器 =====
from .ws import get_ws_manager

ws_manager = get_ws_manager()

# ===== 注册 REST API 路由 =====
from .routes import (
    resources_router, tasks_router, sources_router,
    stats_router, settings_router, chat_router,
    project_router, terminal_router, update_router,
)

app.include_router(resources_router)
app.include_router(tasks_router)
app.include_router(sources_router)
app.include_router(stats_router)
app.include_router(settings_router)
app.include_router(chat_router)
app.include_router(project_router)
app.include_router(terminal_router)
app.include_router(update_router)


# ===== 网页版控制面板（静态前端）=====
from fastapi.staticfiles import StaticFiles

WEB_STATIC_DIR = Path(__file__).resolve().parent / "static"
if WEB_STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_STATIC_DIR), html=True), name="webpanel")
    logger.info(f"🌐 网页版控制面板已挂载: {WEB_STATIC_DIR} → 浏览器访问 http://127.0.0.1:9800/")


# ===== 健康检查 =====
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": _APP_VERSION}


# ===== 版本信息 =====
@app.get("/api/version")
async def version_info():
    return {"name": "7tan-editor", "version": _APP_VERSION}


# ===== WebSocket 端点 =====
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # ===== WebSocket 握手鉴权（防跨站 WebSocket 劫持 CSWSH）=====
    # HTTP 中间件不经过 WS 握手，因此这里必须单独校验：
    # 1) 浏览器发起的连接必带 Origin 头 → 只允许本地页面
    # 2) 无 Origin 的客户端（桌面端/Python websockets 等）→ 放行
    # 3) 若配置了 7TAN_API_TOKEN，本地页面也需携带 ?token=xxx
    origin = ws.headers.get("origin", "")
    query_token = ws.query_params.get("token", "")
    client_host = ws.client.host if ws.client else ""
    is_local = client_host in ("127.0.0.1", "::1", "localhost")

    # 带有效 token 的连接（浏览器远程页面 / API 客户端）→ 放行，token 是最强凭证
    if query_token and query_token == API_TOKEN:
        pass
    elif origin:
        # 浏览器连接必须来自本地页面（防 CSWSH）；远程页面若无 token 一律拒绝
        allowed_origin = (
            origin.startswith("http://127.0.0.1")
            or origin.startswith("http://localhost")
            or origin.startswith("http://[::1]")
        )
        if not allowed_origin or not is_local:
            logger.warning(f"🚫 拒绝未授权 WebSocket 连接: origin={origin}, host={client_host}")
            await ws.close(code=1008, reason="unauthorized")
            return
    elif not is_local:
        # 无 Origin 的远程客户端（非浏览器）必须带 token
        logger.warning(f"🚫 拒绝未授权 WebSocket 连接: host={client_host}, 缺少 token")
        await ws.close(code=1008, reason="unauthorized")
        return

    client_id = await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")
            if msg_type == "chat":
                await _handle_chat(ws, client_id, data)
            elif msg_type == "pipeline":
                await _handle_pipeline(ws, client_id, data)
            elif msg_type == "status":
                await _handle_status(ws, client_id)
            elif msg_type == "jobs":
                await _handle_jobs(ws, client_id)
            elif msg_type == "resources":
                await _handle_resources(ws, client_id)
            elif msg_type == "get_sessions":
                await _handle_get_sessions(ws)
            else:
                await ws.send_json({"type": "error", "data": {"message": f"未知消息类型: {msg_type}"}})
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
        try:
            ws_manager.disconnect(client_id)
        except Exception:
            pass


async def _handle_chat(ws: WebSocket, client_id: str, data: dict):
    """处理聊天消息"""
    import threading
    from ..agent.agent_loop import run_agent_loop
    from ..agent.conversation import save_message
    from ..database.db import get_session, save_message as db_save

    session_id = data.get("session_id", "")
    message = data.get("message", "")
    model = data.get("model", "")

    if not message.strip():
        await ws.send_json({"type": "chat_error", "session_id": session_id, "error": "消息不能为空"})
        return

    loop = asyncio.get_event_loop()

    def run_and_report():
        try:
            save_message(session_id, "user", message)
            result = run_agent_loop(task=message, model_name=model, session_id=session_id)
            save_message(session_id, "assistant", result.get("result", ""), model=model)
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "chat_done",
                    "session_id": session_id,
                    "success": result["success"],
                    "result": result["result"],
                    "cost": result.get("cost", 0),
                }), loop
            )
        except Exception as e:
            logger.error(f"Agent 循环异常: {e}")
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "chat_error",
                    "session_id": session_id,
                    "error": str(e),
                }), loop
            )

    loop.run_in_executor(None, run_and_report)


async def _handle_pipeline(ws: WebSocket, client_id: str, data: dict):
    try:
        from ..pipeline.pipeline import run_full_pipeline
        result = run_full_pipeline()
        await ws.send_json({"type": "pipeline_done", "data": result})
    except Exception as e:
        await ws.send_json({"type": "error", "data": {"message": str(e)}})


async def _handle_status(ws: WebSocket, client_id: str):
    try:
        from ..tools.monitor_tools import get_system_status
        status = get_system_status()
        await ws.send_json({"type": "status", "data": status})
    except Exception as e:
        await ws.send_json({"type": "error", "data": {"message": str(e)}})


async def _handle_jobs(ws: WebSocket, client_id: str):
    try:
        from ..database.connection import get_db
        db = get_db()
        jobs = db.execute("SELECT * FROM task_logs ORDER BY created_at DESC LIMIT 20").fetchall()
        await ws.send_json({
            "type": "jobs",
            "data": [dict(row) for row in jobs],
        })
    except Exception as e:
        await ws.send_json({"type": "error", "data": {"message": str(e)}})


async def _handle_resources(ws: WebSocket, client_id: str):
    try:
        from ..database.connection import get_db
        db = get_db()
        resources = db.execute("SELECT * FROM resources ORDER BY created_at DESC LIMIT 50").fetchall()
        await ws.send_json({
            "type": "resources",
            "data": [dict(row) for row in resources],
        })
    except Exception as e:
        await ws.send_json({"type": "error", "data": {"message": str(e)}})


async def _handle_get_sessions(ws: WebSocket):
    try:
        from ..agent.conversation import get_recent_sessions
        sessions = get_recent_sessions()
        await ws.send_json({"type": "sessions", "data": sessions})
    except Exception as e:
        await ws.send_json({"type": "error", "data": {"message": str(e)}})


def shutdown_server():
    """
    优雅关闭服务器 socket，释放端口。
    在重启流程中，旧进程调用此函数后，新进程可立即绑定端口，
    无需等待重试。此函数幂等，可安全重复调用。
    """
    global _server_socket
    if _server_socket is not None:
        try:
            _server_socket.close()
            logger.info("🔌 服务器 socket 已关闭，端口已释放")
        except Exception as e:
            logger.warning(f"关闭服务器 socket 时出错: {e}")
        finally:
            _server_socket = None


def start_server(host: str = "0.0.0.0", port: int = 9800):
    """
    启动 FastAPI 服务器

    使用预创建的 socket（设置 SO_REUSEADDR），避免重启时
    Windows TIME_WAIT（最长 120 秒）导致端口被占用，新进程无法 bind。
    """
    global _server_socket
    import uvicorn
    import socket

    logger.info(f"🌐 正在启动 API 服务器 on {host}:{port}...")

    # 预创建 socket，在 bind 前设置 SO_REUSEADDR
    # 这样旧进程退出后，新进程可以立即复用端口，无需等待 TIME_WAIT 释放
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    _server_socket = sock

    # 🔧 修复: 重启时旧进程可能仍占用端口（SO_REUSEADDR 在 Windows 上不
    # 允许绑定已被活跃使用的端口）。重试最多 50 秒，等待旧进程退出释放端口。
    # 旧进程的验证周期最长 37 秒（2s 延迟 + 35s 超时），50 秒留有充足余量。
    # 如果旧进程调用了 shutdown_server()，则端口立即可用，无需重试。
    import time as _time
    bind_retry_max = 50
    bind_retry_delay = 0.5
    for _bind_attempt in range(bind_retry_max):
        try:
            sock.bind((host, port))
            break
        except OSError:
            if _bind_attempt < bind_retry_max - 1:
                if _bind_attempt == 0:
                    logger.info(f"⏳ 端口 {port} 被占用，等待旧进程退出...")
                _time.sleep(bind_retry_delay)
                bind_retry_delay = min(bind_retry_delay * 1.3, 3.0)
            else:
                logger.error(f"❌ 端口 {port} 绑定失败，已重试 {bind_retry_max} 次")
                raise

    config = uvicorn.Config(app, log_level="info", log_config=None)
    server = uvicorn.Server(config)

    try:
        server.run(sockets=[sock])
    except Exception as e:
        logger.exception(f"❌ API 服务器异常退出: {e}")
        raise
    finally:
        try:
            sock.close()
        except Exception:
            pass
        _server_socket = None
