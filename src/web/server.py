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
API_TOKEN = os.environ.get("7TAN_API_TOKEN", "")


def _get_project_root():
    """获取项目根目录 — 兼容开发模式和 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


PROJECT_ROOT = _get_project_root()

# 确保 src 目录在 path 中
sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(title="7Tan", version="5.1.0", docs_url=None, redoc_url=None)


# ===== API 安全中间件 =====
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """简单认证：本地请求放行，远程请求需要 token"""
    host = request.client.host if request.client else ""
    path = request.url.path

    # 健康检查和 WebSocket 放行
    if path == "/api/health" or path.startswith("/ws"):
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
    project_router, terminal_router,
)

app.include_router(resources_router)
app.include_router(tasks_router)
app.include_router(sources_router)
app.include_router(stats_router)
app.include_router(settings_router)
app.include_router(chat_router)
app.include_router(project_router)
app.include_router(terminal_router)

# ===== 根路由 =====

@app.get("/")
async def root():
    """根路由 — API 信息"""
    return JSONResponse({"app": "7Tan", "version": app.version, "mode": "desktop"})


@app.get("/api/health")
async def health():
    """健康检查 — 返回版本号和系统状态"""
    try:
        from ..tools.monitor_tools import health_check
        detail = health_check()
    except Exception:
        detail = "ok"
    return JSONResponse({"status": "ok", "version": app.version, "detail": detail})


@app.get("/api/version")
async def version():
    """版本信息"""
    return JSONResponse({"version": app.version, "name": "7Tan"})


# ===== 生命周期 =====

@app.on_event("startup")
async def startup():
    # 确保 CDN 离线缓存目录存在（§21.2）
    cache_dir = PROJECT_ROOT / "data" / "web_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info("🌐 API 服务器启动于 http://localhost:9800")


@app.on_event("shutdown")
async def shutdown():
    logger.info("🌐 API 服务器关闭")


# ===== WebSocket =====

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client_id = await ws_manager.connect(ws)

    try:
        while True:
            data = await ws.receive_json()
            await _handle_ws_message(ws, client_id, data)
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket 断开: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
    finally:
        ws_manager.disconnect(client_id)


async def _handle_ws_message(ws: WebSocket, client_id: str, data: dict):
    """处理 WebSocket 消息 — 路由到具体处理器"""
    msg_type = data.get("type", "")

    if msg_type == "ping":
        await ws.send_json({"type": "pong"})

    elif msg_type == "chat":
        await _handle_chat(ws, client_id, data)

    elif msg_type == "run_pipeline":
        await _handle_pipeline(ws, client_id, data)

    elif msg_type == "get_status":
        await _handle_status(ws, client_id)

    elif msg_type == "get_jobs":
        await _handle_jobs(ws, client_id)

    elif msg_type == "get_resources":
        await _handle_resources(ws, client_id)

    elif msg_type == "confirm_response":
        await ws_manager.handle_message(client_id, data)

    elif msg_type == "get_chat_history":
        await _handle_get_chat_history(ws, data)

    elif msg_type == "get_sessions":
        await _handle_get_sessions(ws)

    else:
        await ws.send_json({"type": "error", "data": {"message": f"未知消息类型: {msg_type}"}})


async def _handle_chat(ws: WebSocket, client_id: str, data: dict):
    """处理 AI 对话"""
    message = data.get("message", "")
    model = data.get("model")
    session_id = data.get("session_id")

    from ..agent.conversation import create_session, save_message

    if not session_id:
        session_id = create_session()

    save_message(session_id, "user", message)
    await ws.send_json({"type": "chat_start", "session_id": session_id})

    loop = asyncio.get_event_loop()

    def run_and_report():
        try:
            from ..agent.agent_loop import run_agent_loop
            result = run_agent_loop(task=message, session_id=session_id, model_name=model)
            save_message(session_id, "assistant", result.get("result", ""))
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


async def _handle_get_chat_history(ws: WebSocket, data: dict):
    session_id = data.get("session_id")
    try:
        from ..agent.conversation import get_session_messages
        messages = get_session_messages(session_id) if session_id else []
        await ws.send_json({
            "type": "chat_history",
            "session_id": session_id,
            "data": messages,
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


def start_server(host: str = "0.0.0.0", port: int = 9800):
    """启动 FastAPI 服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
