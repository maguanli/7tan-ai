"""
后端 API 服务器 — FastAPI + WebSocket + REST API
纯 API 模式，桌面版使用 PyQt6 原生控件
"""
import sys
import asyncio
import collections
import ipaddress
import threading as _threading
import time as _time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse
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

# ===== 局域网免 Token 开关（config.yaml -> web.allow_lan）=====
_ALLOW_LAN = False
try:
    from src.config.loader import load_config
    _ALLOW_LAN = bool(load_config().get("web", {}).get("allow_lan", False))
except Exception:
    _ALLOW_LAN = False


def _is_lan_address(host: str) -> bool:
    """判断 IP 是否为局域网/私有地址（192.168/16、10/8、172.16/12、链路本地等）"""
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
        return ip.is_private or ip.is_link_local or ip.is_loopback or (not ip.is_global)
    except ValueError:
        return False


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


@app.on_event("startup")
async def _capture_event_loop():
    """捕获事件循环，供日志 sink 线程安全广播 WS 消息使用。"""
    global _APP_LOOP
    _APP_LOOP = asyncio.get_running_loop()


# ===== API 安全中间件 =====
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """简单认证：本地请求放行，远程请求需要 token"""
    host = request.client.host if request.client else ""
    path = request.url.path

    # 健康检查、WebSocket、静态页面（网页版前端）放行；仅 /api/* 需鉴权
    if path == "/api/health" or path.startswith("/ws") or not path.startswith("/api/"):
        return await call_next(request)

    # 会员登录/刷新接口豁免 Token 鉴权：登录是获取凭据的入口，
    # 若也要求 API Token 会形成死锁（远程用户无法登录 → 无法获得会员身份 → 也无法使用功能）
    if path in ("/api/license/login", "/api/license/refresh", "/api/license/status"):
        return await call_next(request)

    # 本地请求放行
    if host in ("127.0.0.1", "::1", "localhost"):
        return await call_next(request)

    # 局域网免 Token：config.yaml web.allow_lan=true 时放行私有网段设备
    if _ALLOW_LAN and _is_lan_address(host):
        return await call_next(request)

    # 远程请求需要 API Token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if API_TOKEN and token == API_TOKEN:
        return await call_next(request)

    logger.warning(f"未授权的远程请求: {host} -> {path}")
    return JSONResponse({"error": "unauthorized"}, status_code=401)


class _NoCacheASGI:
    """ASGI 中间件：在 http.response.start 事件层为静态资源注入 no-store 头。

    说明：用 BaseHTTPMiddleware 事后修改 resp.headers 不可行——
    start 事件已先行发送给客户端，事后改头客户端收不到。
    纯 ASGI 方案直接拦截事件流，最可靠。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")

        async def send_wrapper(message):
            if message["type"] == "http.response.start" and \
                    not path.startswith("/api/") and path != "/ws":
                headers = [
                    (k, v) for k, v in message.get("headers", [])
                    if k.lower() != b"cache-control"
                ]
                headers.append((b"cache-control", b"no-store, max-age=0"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(_NoCacheASGI)

# ===== WebSocket 管理器 =====
from .ws import get_ws_manager

ws_manager = get_ws_manager()

# ===== 实时日志广播（网页版实时控制台） =====
# 内存环形缓冲：网页控制台优先读它（比读日志文件快且实时）
_LOG_RING: collections.deque = collections.deque(maxlen=1000)
_APP_LOOP: Optional[asyncio.AbstractEventLoop] = None

# —— 与桌面版控制台对齐：时间窗口去重（3s 精确 + 2s 模糊）+ 启动噪声过滤 ——
_DEDUP_MAP: dict = {}
_DEDUP_LOCK = _threading.Lock()
_DEDUP_WINDOW = 3.0
_DEDUP_FUZZY_WINDOW = 2.0

_NOISE_PATTERNS = [
    '🔧 注册工具', '📦 插件已加载', '✅ 数据库初始化完成',
    '[系统] loguru 控制台 sink 已连接', '[系统] 标准 logging 桥接已安装',
    '[系统] Python stdout/stderr 重定向已安装', '[系统] OS 管道已安装',
    '[系统] GUI 模式，跳过 OS 管道', '[系统] loguru sink 失败',
    'Sending HTTP Request',
]

# —— HTTP 访问日志噪声（uvicorn access log）：轮询端点每 2 秒刷 2 条，
# 会淹没 agent 的 💬 Agent / 工具调用日志，必须过滤。 ——
_HTTP_ACCESS_NOISE = (
    '/api/logs/recent',    # 控制台轮询
    '/api/health',         # 健康检查
    '/api/license/status', # 授权轮询
    '/api/stats/dashboard',# 仪表盘轮询
    '/ws',                 # WebSocket
    '"GET / HTTP/1.1',     # 页面访问
    '"GET /style.css',     # 静态样式
    '"GET /app.js',        # 静态脚本
    '"GET /favicon',       # 图标
)

_WS_CONNECT_NOISE = (
    '\"WebSocket /ws\" [accepted]',
    'connection open',
    'WebSocket 连接:',
    'WebSocket 断开:',
    'WebSocket 已连接',
    'WebSocket 客户端已连接',
    'WebSocket 客户端断开',
)


def _is_http_access_noise(line: str) -> bool:
    """检测是否 HTTP 访问日志噪声（uvicorn access log / WS 连接日志）。"""
    # 先查 WS 连接噪声（这些行没有 GET/POST 字样，必须先判断）
    for p in _WS_CONNECT_NOISE:
        if p in line:
            return True
    if '"GET ' not in line and '"POST ' not in line and '"PUT ' not in line:
        return False
    if 'HTTP/1.1' not in line:
        return False
    for p in _HTTP_ACCESS_NOISE:
        if p in line:
            return True
    # 通用兜底：任意 /api/ 访问日志（含 200）都属于噪声，控制台只关心业务日志
    if '/api/' in line:
        return True
    return False


def _ws_log_sink(message: str) -> None:
    """loguru sink — 写入环形缓冲 + 异步广播给所有 WebSocket 客户端。

    与桌面版 console_panel 对齐：入口做时间窗口去重（WS 广播与轮询
    双通道防重复）与噪声过滤（保持控制台清爽，不显示启动噪音）。
    """
    try:
        line = message.rstrip()
        if not line.strip():
            return
        if _is_http_access_noise(line):
            return
        for np_ in _NOISE_PATTERNS:
            if np_ in line:
                return
        h = hash(line)
        h_fuzzy = hash(line[:60])
        now = _time.time()
        with _DEDUP_LOCK:
            last = _DEDUP_MAP.get(h)
            if last is not None and (now - last) < _DEDUP_WINDOW:
                return
            last_f = _DEDUP_MAP.get(h_fuzzy)
            if last_f is not None and (now - last_f) < _DEDUP_FUZZY_WINDOW:
                return
            _DEDUP_MAP[h] = now
            _DEDUP_MAP[h_fuzzy] = now
            if len(_DEDUP_MAP) > 10000:
                _DEDUP_MAP.clear()
        _LOG_RING.append(line)
    except Exception:
        pass
    loop = _APP_LOOP
    if loop is not None and loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(
                ws_manager.send_log("INFO", message.rstrip()), loop)
        except Exception:
            pass


# 注册 loguru sink（INFO 及以上；enqueue=True 走独立线程，不阻塞业务）
logger.add(
    _ws_log_sink,
    level="INFO",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {message}",
)

# ===== 标准 logging 桥接（agent_loop 等模块的关键日志 → 实时控制台） =====
# agent_loop.py 用 logging.getLogger 打 💬 Agent / 工具调用等日志（标准 logging），
# loguru 不会自动接管标准 logging，桌面版靠 console_panel._LoggingBridge 才能显示，
# WEB 版此前无桥接 → 💬 Agent 内容不进环形缓冲/WS 广播，实时控制台看不到。
import logging as _logging


class _StdLogBridge(_logging.Handler):
    """标准 logging → WEB 实时控制台桥接。"""

    def emit(self, record: _logging.LogRecord) -> None:
        try:
            _ws_log_sink(self.format(record))
        except Exception:
            pass


def _install_std_log_bridge() -> None:
    # 抑制 uvicorn 访问日志（access log 是 INFO 级，会刷屏控制台）
    for _uv_name in ('uvicorn.access', 'uvicorn.error'):
        _uv_logger = _logging.getLogger(_uv_name)
        _uv_logger.setLevel(_logging.WARNING)
    root = _logging.getLogger()
    # 放开 root 级别：默认 WARNING 会让 agent_loop 的 INFO（💬 Agent 等）根本不产生记录
    if root.level > _logging.INFO:
        root.setLevel(_logging.INFO)
    for h in root.handlers:
        if isinstance(h, _StdLogBridge):
            return
    h = _StdLogBridge()
    h.setLevel(_logging.INFO)
    h.setFormatter(_logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(h)


_install_std_log_bridge()

# ===== stdout/stderr 重定向（与桌面版控制台对齐：捕获 print 输出） =====
# 桌面版 console_panel 有 Python 重定向层，WEB 版此前没有 → print() 输出的内容
# （部分模块的关键信息）WEB 控制台看不到，与桌面版内容不一致。这里补上。
import io as _io


class _StreamRedirector(_io.TextIOBase):
    """线程安全的 stdout/stderr → 实时控制台 重定向。

    把 print() 输出按行送入环形缓冲 + WS 广播，同时写回原流
    （pythonw 下原流可能为 None，自动跳过），不破坏原有输出。
    """

    def __init__(self, original):
        self._original = original
        self._buf = []
        self._lock = _threading.Lock()

    def write(self, s: str) -> int:
        if not s:
            return 0
        with self._lock:
            self._buf.append(s)
            while True:
                joined = "".join(self._buf)
                idx = joined.find("\n")
                if idx < 0:
                    break
                line = joined[:idx]
                rest = joined[idx + 1:]
                self._buf = [rest] if rest else []
                if line.strip():
                    _ws_log_sink(line)
            try:
                if self._original is not None:
                    self._original.write(s)
                    self._original.flush()
            except Exception:
                pass
        return len(s)

    def flush(self):
        with self._lock:
            if self._buf:
                _ws_log_sink("".join(self._buf).rstrip())
                self._buf = []
            try:
                if self._original is not None:
                    self._original.flush()
            except Exception:
                pass


_STREAM_REDIRECT_INSTALLED = False


def _install_stream_redirect() -> None:
    """安装 stdout/stderr → 实时控制台 重定向（幂等，只装一次）。"""
    global _STREAM_REDIRECT_INSTALLED
    if _STREAM_REDIRECT_INSTALLED:
        return
    try:
        sys.stdout = _StreamRedirector(sys.__stdout__)
        sys.stderr = _StreamRedirector(sys.__stderr__)
        _STREAM_REDIRECT_INSTALLED = True
        logger.info("[系统] Python stdout/stderr 重定向已安装（WEB 控制台）")
    except Exception as e:
        logger.warning(f"[系统] stdout/stderr 重定向失败: {e}")


_install_stream_redirect()

# ===== 注册 REST API 路由 =====
from .routes import (
    resources_router, tasks_router, sources_router,
    stats_router, settings_router, chat_router,
    project_router, terminal_router, update_router,
    code_router, license_router, adapt_router, mind_router,
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
app.include_router(code_router)
app.include_router(license_router)
app.include_router(adapt_router)
app.include_router(mind_router)


# ===== 网页版控制面板（静态前端）=====
# ⚠️ 注意：mount('/') 会拦截所有未匹配路径，必须等 /ws、/api/* 等路由全部注册完
# 才能挂载，否则 WebSocket 会被静态处理器吞掉（返回 500）。挂载逻辑见文件末尾 _mount_web_panel()。
from fastapi.staticfiles import StaticFiles

WEB_STATIC_DIR = Path(__file__).resolve().parent / "static"


# ===== 健康检查 =====
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": _APP_VERSION}


# ===== 版本信息 =====
@app.get("/api/version")
async def version_info():
    return {"name": "7tan-editor", "version": _APP_VERSION}


# ===== 系统状态（网页版仪表盘用） =====
@app.get("/api/status")
async def api_status():
    try:
        from src.tools.monitor_tools import get_system_status
        return get_system_status()
    except Exception as e:
        return {"error": str(e)}


# ===== 系统日志（网页版控制台视图用） =====
@app.get("/api/logs/recent")
async def api_logs_recent(lines: int = 200, source: str = "file"):
    """读取最近日志：source=ring 读内存实时缓冲（网页控制台），source=file 读日志文件尾部（系统日志视图）。"""
    if source == "ring":
        tail = list(_LOG_RING)[-min(lines, len(_LOG_RING)):]
        return {"file": None, "lines": tail, "source": "ring"}
    try:
        from datetime import date
        logs_dir = PROJECT_ROOT / "logs"
        if not logs_dir.exists():
            return {"file": None, "lines": []}
        today = date.today().strftime("%Y-%m-%d")
        # 优先今天的 app 日志，其次最新 app 日志
        candidates = sorted(logs_dir.glob("app_*.log"), reverse=True)
        if not candidates:
            return {"file": None, "lines": []}
        target = next((c for c in candidates if today in c.name), candidates[0])
        raw = target.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = raw[-min(lines, len(raw)):] if raw else []
        return {"file": target.name, "lines": tail}
    except Exception as e:
        return {"file": None, "lines": [], "error": str(e)}


@app.post("/api/logs/clear")
async def api_logs_clear():
    """清空实时控制台内存环形缓冲（网页控制台【清】按钮）。

    修复：此前清空只清前端 DOM，后端 _LOG_RING 仍有旧日志，
    3 秒轮询 /api/logs/recent 又把旧日志拉回来 → 看起来"没清空"。
    """
    try:
        with _DEDUP_LOCK:
            cleared = len(_LOG_RING)
            _LOG_RING.clear()
            _DEDUP_MAP.clear()
        return {"ok": True, "cleared": cleared}
    except Exception as e:
        logger.warning(f"清空控制台环形缓冲失败: {e}")
        return {"ok": False, "cleared": 0, "error": str(e)}


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
    # 局域网免 Token：config.yaml web.allow_lan=true 时放行私有网段设备
    is_trusted = is_local or (_ALLOW_LAN and _is_lan_address(client_host))

    # 带有效 token 的连接（浏览器远程页面 / API 客户端）→ 放行，token 是最强凭证
    if query_token and query_token == API_TOKEN:
        pass
    elif not is_trusted:
        # 可信主机（本地/局域网免Token开启）之外的连接必须带 token
        logger.warning(f"🚫 拒绝未授权 WebSocket 连接: origin={origin}, host={client_host}")
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
            # 本地 7Tan 模型分支：不走 LLM API，直接调用本地预测引擎 + 言语系统
            from ..agent.world_model import is_7tan_model, get_tan_model, ensure_7tan_model_config
            if is_7tan_model(model):
                ensure_7tan_model_config()
                logger.info(f"🌍 7Tan模型（本地引擎）处理消息: {message[:50]}")
                try:
                    _hist = []
                    try:
                        from ..agent.conversation import get_session_messages
                        _msgs = get_session_messages(session_id, limit=50)
                        _hist = [
                            {"role": m.get("role"), "content": m.get("content", "")}
                            for m in _msgs
                            if m.get("role") in ("user", "assistant")
                        ]
                        if _hist and _hist[-1].get("role") == "user" and _hist[-1].get("content", "").strip() == message.strip():
                            _hist = _hist[:-1]
                    except Exception:
                        _hist = []
                    reply = get_tan_model().respond(message, history=_hist)
                except Exception as e:
                    logger.error(f"7Tan 模型响应失败: {e}")
                    reply = f"❌ 7Tan 模型引擎异常: {e}"
                save_message(session_id, "assistant", reply, model=model)
                asyncio.run_coroutine_threadsafe(
                    ws.send_json({
                        "type": "chat_done",
                        "session_id": session_id,
                        "success": True,
                        "result": reply,
                        "cost": 0,
                    }), loop
                )
                return
            result = run_agent_loop(task=message, model_name=model, session_id=session_id, max_iterations=1000)  # 迭代上限1000（按用户要求恢复）
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
        # WEB 版无完整流水线入口（pipeline 模块无 run_full_pipeline），返回明确提示而非崩连接
        await ws.send_json({"type": "error", "data": {"message": "pipeline 消息暂不支持（WEB 版）"}})
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
        from ..database.db import get_session, TaskLog
        session = get_session()
        try:
            rows = session.query(TaskLog).order_by(TaskLog.id.desc()).limit(20).all()
            data = [{c.name: getattr(r, c.name) for c in TaskLog.__table__.columns} for r in rows]
        finally:
            session.close()
        await ws.send_json({"type": "jobs", "data": data})
    except Exception as e:
        await ws.send_json({"type": "error", "data": {"message": str(e)}})


async def _handle_resources(ws: WebSocket, client_id: str):
    try:
        from ..database.db import get_session, Resource
        session = get_session()
        try:
            rows = session.query(Resource).order_by(Resource.created_at.desc()).limit(50).all()
            data = [{c.name: getattr(r, c.name) for c in Resource.__table__.columns} for r in rows]
        finally:
            session.close()
        await ws.send_json({"type": "resources", "data": data})
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

    # 🔧 修复：统一工作目录到项目根目录。
    # token_store / 数据库等模块使用相对路径（data/auth/token.dat 等），
    # 依赖进程 cwd。若 WEB 进程与桌面版 cwd 不一致，会导致读不到登录态、
    # 找不到数据文件。这里强制 chdir 到项目根目录，与桌面版保持一致。
    try:
        os.chdir(str(PROJECT_ROOT))
        logger.info(f"📁 已切换工作目录到项目根: {PROJECT_ROOT}")
    except Exception as _cwd_err:
        logger.warning(f"⚠️ 切换工作目录失败: {_cwd_err}")

    logger.info(f"🌐 正在启动 API 服务器 on {host}:{port}...")

    # 🎤 注册全局语音朗读桥（与桌面版一致）：Agent 最终回复 → 后端 TTS（Piper/Edge）朗读，
    # 受数据库 app_settings.voice_mode 开关控制。否则 WEB 版 Agent 回复不会朗读。
    try:
        from src.agent.speak_bridge import init_global_tts
        init_global_tts()
    except Exception as _tts_err:
        logger.warning(f"[TTS-Bridge] 初始化失败: {_tts_err}")

    # 💬 注册 WEB 版实时控制台朗读监听：监听标准 logging 的 💬 Agent 日志行
    # （中间迭代 + 最终回复），与桌面版 console_panel 行为一致。
    # 没有它，WEB 版实时控制台中的 Agent 说话内容不会朗读。
    try:
        from src.agent.web_console_tts import init_web_console_tts
        init_web_console_tts()
    except Exception as _wtts_err:
        logger.warning(f"[TTS-Web] 初始化失败: {_wtts_err}")

    # 🔄 绿色版开机自启路径自愈：WEB 服务每次启动静默校准注册表自启路径。
    # 绿色版（解压即用）用户可能移动/重命名软件目录，自启条目会指向旧路径失效；
    # 这里每次启动都校验一次，路径不一致自动更新，保证「移动目录后依然开机自启」。
    try:
        from tools.web_autostart import install as _autostart_install
        from tools.web_autostart import install_protocol as _protocol_install
        _autostart_install(silent=True)
        _protocol_install(silent=True)
    except Exception as _autostart_err:
        logger.debug(f"[autostart] 自启/协议路径校准跳过: {_autostart_err}")

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


# ===== 网页版控制面板（静态前端）— 必须放在所有路由注册之后 =====
def _mount_web_panel():
    """挂载静态前端。必须在所有路由注册完成后调用，
    否则 mount('/') 会拦截 /ws、/api/* 等请求（Starlette 按注册顺序匹配）。"""
    _logo_dir = PROJECT_ROOT / "data" / "logo"
    if _logo_dir.exists():
        app.mount("/logo", StaticFiles(directory=str(_logo_dir)), name="logo")
        logger.info(f"🖼️ LOGO 静态目录已挂载: {_logo_dir} → /logo")
    @app.get("/", include_in_schema=False)
    async def web_index():
        """Home: no-cache so browser always fetches latest frontend."""
        idx = WEB_STATIC_DIR / "index.html"
        if idx.exists():
            return FileResponse(idx, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        return JSONResponse({"error": "web panel not found"}, status_code=404)

    if WEB_STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(WEB_STATIC_DIR), html=True), name="webpanel")
        logger.info(f"🌐 网页版控制面板已挂载: {WEB_STATIC_DIR} → 浏览器访问 http://127.0.0.1:9900/")


_mount_web_panel()
