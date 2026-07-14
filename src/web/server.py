"""
Web 服务器 — FastAPI + WebSocket + REST API
详见架构文档 §21
"""
import sys
import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger


def _get_project_root():
    """获取项目根目录 — 兼容开发模式和 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def _get_static_dir():
    """获取静态文件目录"""
    if getattr(sys, 'frozen', False):
        # PyInstaller: sys._MEIPASS 中是只读的 bundled data
        return Path(sys._MEIPASS) / "src" / "web" / "static"
    return Path(__file__).parent / "static"


PROJECT_ROOT = _get_project_root()

# 确保 src 目录在 path 中
sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(title="7坛AI小编", version="5.1.0", docs_url=None, redoc_url=None)

# ===== WebSocket 管理器 =====
from .ws import get_ws_manager

ws_manager = get_ws_manager()

# ===== 注册 REST API 路由 =====
from .routes import (
    resources_router, tasks_router, sources_router,
    stats_router, settings_router, chat_router,
)

app.include_router(resources_router)
app.include_router(tasks_router)
app.include_router(sources_router)
app.include_router(stats_router)
app.include_router(settings_router)
app.include_router(chat_router)

# ===== 挂载静态文件 =====
static_dir = _get_static_dir()
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ===== 根路由 — 返回前端页面 =====

TEMPLATE_DIR = _get_static_dir().parent / "templates"


@app.get("/")
async def root():
    """返回前端首页"""
    index_file = TEMPLATE_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>7坛AI小编</h1><p>前端文件未找到</p>", status_code=404)


@app.get("/api/health")
async def health():
    """健康检查"""
    return JSONResponse({"status": "ok", "version": app.version})


# ===== 生命周期 =====

@app.on_event("startup")
async def startup():
    # 确保 CDN 离线缓存目录存在（§21.2）
    cache_dir = PROJECT_ROOT / "data" / "web_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info("🌐 Web 服务器启动于 http://localhost:9800")


@app.on_event("shutdown")
async def shutdown():
    logger.info("🌐 Web 服务器关闭")


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
        # 转发给 ws_manager 处理（自修改确认）
        await ws_manager.handle_message(client_id, data)

    elif msg_type == "get_chat_history":
        await _handle_get_chat_history(ws, data)

    elif msg_type == "get_sessions":
        await _handle_get_sessions(ws)

    else:
        await ws.send_json({"type": "error", "data": {"message": f"未知消息类型: {msg_type}"}})


async def _handle_chat(ws: WebSocket, client_id: str, data: dict):
    """处理 AI 对话 — 复用已有 session 或创建新的"""
    message = data.get("message", "")
    model = data.get("model")
    session_id = data.get("session_id")  # 前端可能传入已有 session_id

    from ..agent.conversation import create_session, save_message

    # 如果没有传入 session_id 则创建新会话
    if not session_id:
        session_id = create_session()

    # 保存用户消息到数据库
    save_message(session_id, "user", message)

    await ws.send_json({"type": "chat_start", "session_id": session_id})

    # 使用模块级线程池（避免局部 executor 被 GC）
    loop = asyncio.get_event_loop()

    def run_and_report():
        try:
            from ..agent.agent_loop import run_agent_loop
            result = run_agent_loop(task=message, session_id=session_id, model_name=model)
            # 保存 AI 回复到数据库
            save_message(session_id, "assistant", result.get("result", ""))
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "chat_done",
                    "session_id": session_id,
                    "success": result["success"],
                    "result": result["result"],
                    "cost": result.get("cost", 0),
                    "iterations": result.get("iterations", 0),
                }),
                loop,
            )
        except Exception as e:
            logger.error(f"对话执行失败: {e}")
            save_message(session_id, "assistant", f"❌ {e}")
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "chat_done",
                    "session_id": session_id,
                    "success": False,
                    "result": str(e),
                }),
                loop,
            )

    # 使用模块级线程池（与 api_chat.py 共享）
    from .routes.api_chat import _chat_executor
    _chat_executor.submit(run_and_report)


async def _handle_get_chat_history(ws: WebSocket, data: dict):
    """加载指定会话的对话历史"""
    session_id = data.get("session_id", "")
    from ..agent.conversation import get_session_messages
    messages = get_session_messages(session_id) if session_id else []
    await ws.send_json({
        "type": "chat_history",
        "session_id": session_id,
        "messages": messages,
    })


async def _handle_get_sessions(ws: WebSocket):
    """获取最近会话列表"""
    from ..agent.conversation import get_recent_sessions
    sessions = get_recent_sessions()
    await ws.send_json({
        "type": "sessions_list",
        "sessions": sessions,
    })


async def _handle_pipeline(ws: WebSocket, client_id: str, data: dict):
    """处理流水线任务"""
    from ..pipeline.pipeline import Pipeline
    from ..pipeline.task_queue import get_task_queue

    task_desc = data.get("task", "")
    tq = get_task_queue()

    # 通过任务队列提交（带进度推送）
    def run_pipeline_task():
        pipeline = Pipeline()
        return pipeline.run(task=task_desc)

    task_id = tq.submit_function(
        name=f"流水线: {task_desc[:40]}",
        func=run_pipeline_task,
        description=task_desc,
    )

    await ws.send_json({
        "type": "pipeline_queued",
        "task_id": task_id,
        "message": "任务已提交到队列",
    })


async def _handle_status(ws: WebSocket, client_id: str):
    """系统状态"""
    from ..tools.monitor_tools import get_system_status
    status = get_system_status()
    await ws.send_json({"type": "status", "data": status})


async def _handle_jobs(ws: WebSocket, client_id: str):
    """调度器状态"""
    from ..scheduler.scheduler import get_jobs_status
    jobs = get_jobs_status()
    await ws.send_json({"type": "jobs", "data": jobs})


async def _handle_resources(ws: WebSocket, client_id: str):
    """资源列表"""
    from ..database.db import get_session, Resource
    session = get_session()
    try:
        resources = session.query(Resource).order_by(
            Resource.created_at.desc()
        ).limit(50).all()
        await ws.send_json({
            "type": "resources",
            "data": [r.to_dict() for r in resources],
        })
    finally:
        session.close()


# ===== REST API =====

@app.get("/api/health")
async def health():
    from ..tools.monitor_tools import health_check
    return {"status": "ok", "detail": health_check()}


@app.get("/api/status")
async def status():
    from ..tools.monitor_tools import get_system_status
    return {"status": get_system_status()}


@app.get("/api/costs")
async def costs(days: int = 7):
    from ..tools.monitor_tools import get_cost_report
    return {"report": get_cost_report(days=days)}


@app.get("/api/jobs")
async def jobs():
    from ..scheduler.scheduler import get_jobs_status
    return {"jobs": get_jobs_status()}


@app.get("/")
async def index():
    """返回前端页面"""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>7坛AI小编</h1><p>前端页面未找到</p>")


def start_server(host: str = "0.0.0.0", port: int = 9800):
    """启动 Web 服务器"""
    import uvicorn
    logger.info(f"🌐 启动 Web 服务器: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
