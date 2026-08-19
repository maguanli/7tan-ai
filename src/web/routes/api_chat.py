"""
对话 API — 支持 SSE 流式响应
POST /api/chat/send    — 发送消息
GET  /api/chat/history — 获取历史
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import threading
import asyncio
import os
import sys
import time
import uuid
import subprocess
from pathlib import Path

from ...agent.agent_loop import run_agent_loop, run_agent_loop_streaming, AbortSignal
from ...tools.registry import get_all_tools
from ... import tools as _tools  # noqa: F401 触发 @register_tool 装饰器
from ...agent.conversation import (
    create_session, save_message, get_session_messages,
    get_recent_sessions, delete_session,
)
from loguru import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ============================================================
# 图片上传与视觉分析（WEB 版聊天配图）
# ============================================================
_ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _project_root() -> Path:
    """项目根目录（src/web/routes/api_chat.py → 上溯 4 级）"""
    return Path(__file__).resolve().parent.parent.parent.parent


def _find_camera_do() -> Optional[str]:
    """定位视觉分析后端脚本 camera_do.py（GLM-4V）"""
    root = _project_root()
    candidates = [
        root / "tools" / "camera_vision" / "camera_do.py",
        Path("tools/camera_vision/camera_do.py"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _analyze_image(image_path: str) -> str:
    """调用视觉大模型（GLM-4V）分析用户上传的图片，返回文字描述。
    失败/未配置/超时返回空字符串，不阻断聊天。"""
    do = _find_camera_do()
    if not do:
        logger.warning("未找到 camera_do.py，跳过图片分析")
        return ""
    try:
        r = subprocess.run(
            [sys.executable, do, "analyze", "--image", image_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, cwd=str(_project_root()),
            creationflags=_CREATE_NO_WINDOW,
        )
        out = (r.stdout or "").strip()
        if r.returncode != 0:
            logger.warning(f"图片分析失败 exit={r.returncode}: {(r.stderr or '')[-500:]}")
            return ""
        return out[-3000:]
    except subprocess.TimeoutExpired:
        logger.warning("图片分析超时")
        return ""
    except Exception as e:
        logger.warning(f"图片分析异常: {e}")
        return ""


def _compose_message(req: "ChatRequest") -> str:
    """组装最终用户消息：纯文本 / 文本+图片视觉描述"""
    msg = (req.message or "").strip()
    if not req.image_path:
        return msg
    path = req.image_path.strip()
    if not os.path.exists(path):
        logger.warning(f"图片路径不存在: {path}")
        return msg
    desc = _analyze_image(path)
    if not desc:
        return msg
    note = f"[用户上传图片：{os.path.basename(path)}]\n图片内容：{desc}"
    return f"{msg}\n\n{note}" if msg else note


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """上传聊天配图 → 保存到 data/uploads/，返回本地路径供视觉分析"""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="未收到文件")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail=f"仅支持图片格式: {', '.join(sorted(_ALLOWED_IMAGE_EXT))}")
    upload_dir = _project_root() / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"chat_{time.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    dest = upload_dir / name
    size = 0
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_IMAGE_SIZE:
                    raise HTTPException(status_code=413, detail="图片超过 10MB 上限")
                f.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        logger.error(f"上传保存失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")
    logger.info(f"📎 聊天图片上传成功: {dest.name} ({size} bytes)")
    return {"path": str(dest), "name": file.filename, "size": size}

# 用户中止标志 — 由 abort 端点设置，由 agent_loop 检查
_abort_flags: dict[str, threading.Event] = {}

def _get_agent_loop_timeout() -> int:
    """从配置读取超时时间，默认 600 秒"""
    try:
        from ...config.loader import load_config
        config = load_config()
        return config.get("agent", {}).get("loop_timeout", 600)
    except Exception:
        return 600

# 每次请求动态读取，不使用模块级缓存
# AGENT_LOOP_TIMEOUT 已改为惰性函数调用


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    image_path: Optional[str] = None  # 用户上传的图片本地路径（视觉分析用）


class ChatResponse(BaseModel):
    session_id: str
    success: bool
    result: str
    cost: float = 0
    iterations: int = 0
    tokens: int = 0
    model: str = ""  # 生成该回复的 AI 模型名


def _resolve_model_name(model_name: str) -> str:
    """解析实际使用的模型名：显式传入优先；否则取数据库激活配置的模型"""
    if model_name and model_name.strip():
        return model_name.strip()
    try:
        from ...agent.model_manager import get_model
        return get_model(None).model_name or ""
    except Exception:
        return ""


def _load_system_prompt() -> str:
    """加载系统提示词：数据库优先 → 文件回退 → 内置默认"""
    # 1. 数据库（管理员在设置页面修改的）
    try:
        from ...database.db import get_prompt_from_db
        db_prompt = get_prompt_from_db("system")
        if db_prompt and db_prompt.get("content", "").strip():
            return db_prompt["content"].strip()
    except Exception:
        pass

    # 2. 本地文件（开发者直接编辑的）
    try:
        from pathlib import Path
        prompt_path = Path("data/prompts/system.txt")
        if prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8").strip()
            if content:
                return content
    except Exception:
        pass

    # 3. 内置默认
    try:
        from ...agent.prompts import DEFAULT_PROMPTS
        return DEFAULT_PROMPTS.get("system", "")
    except Exception:
        pass

    return ""


@router.post("/send")
async def send_message(req: ChatRequest):
    """发送对话消息"""
    session_id = req.session_id or create_session()
    system_prompt = _load_system_prompt()
    used_model = _resolve_model_name(req.model)

    # 组装用户消息（若带图片：先视觉分析，描述并入消息）
    user_message = _compose_message(req)

    # 保存用户消息
    save_message(session_id, "user", user_message)

    # 创建中止标志（供 abort 端点和 agent_loop 检查）
    abort_event = AbortSignal()
    _abort_flags[session_id] = abort_event

    try:
        # 在线程中运行 Agent（threading.Thread，避免 ThreadPoolExecutor 与 PyQt6 冲突）
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def _run_agent():
            try:
                result = run_agent_loop(
                    task=user_message,
                    session_id=session_id,
                    model_name=used_model,
                    tools=get_all_tools(),
                    abort_event=abort_event,
                    system_prompt=system_prompt,
                    max_iterations=1000,  # 迭代上限1000（按用户要求恢复）
                )
                _safe_loop_call(loop, future.set_result, result)
            except Exception as e:
                _safe_loop_call(loop, future.set_exception, e)

        threading.Thread(target=_run_agent, daemon=True).start()

        # 🔒 超时保护：最长等待 AGENT_LOOP_TIMEOUT 秒
        # 防止 AI API 调用挂起时后端无限等待
        try:
            result = await asyncio.wait_for(future, timeout=_get_agent_loop_timeout())
        except asyncio.TimeoutError:
            logger.error(f"⏰ Agent 循环超时 ({_get_agent_loop_timeout()}s)，会话: {session_id}")
            save_message(session_id, "assistant", f"⏰ 请求超时（{_get_agent_loop_timeout()}秒），请重试或简化问题。")
            raise HTTPException(
                status_code=504,
                detail=f"AI 请求超时（{_get_agent_loop_timeout()}秒），请稍后重试。如果是复杂任务，尝试分步执行。"
            )

        # 保存 AI 回复（带模型名）
        save_message(session_id, "assistant", result.get("result", ""), model=used_model)

        return ChatResponse(
            session_id=session_id,
            success=result["success"],
            result=result["result"],
            cost=result.get("cost", 0),
            iterations=result.get("iterations", 0),
            tokens=result.get("total_tokens", 0),
            model=used_model,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对话失败: {e}")
        save_message(session_id, "assistant", f"❌ {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _abort_flags.pop(session_id, None)


# ThreadPoolExecutor 用于 SSE 流式响应（惰性初始化）
_executor = None


def _get_executor():
    global _executor
    if _executor is None:
        import concurrent.futures
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="chat-stream")
    return _executor


@router.post("/send/stream")
async def send_message_stream(req: ChatRequest, request: Request):
    """SSE 流式发送对话消息 — 逐步返回思考过程和结果"""
    session_id = req.session_id or create_session()
    used_model = _resolve_model_name(req.model)
    # 组装用户消息（若带图片：先视觉分析，描述并入消息）
    user_message = _compose_message(req)
    save_message(session_id, "user", user_message)
    
    # 创建中止标志
    abort_event = AbortSignal()
    # 🛡️ 并发保护：同一会话已有任务在跑 → 先中止旧任务，避免多个 agent 同时空转
    _old_evt = _abort_flags.get(session_id)
    if _old_evt is not None and not _old_evt.is_set():
        _old_evt.set("concurrent")
        logger.warning(f"⚠️ [API] 会话 {session_id} 已有任务在执行，已中止旧任务（防并发失控）")
    _abort_flags[session_id] = abort_event
    
    async def event_generator():
        try:
            async for ev in _stream_events():
                yield ev
        finally:
            # 生成器真正结束时才清理中止标志（不能在 return 时 pop，否则中止按钮失效）
            _abort_flags.pop(session_id, None)

    async def _stream_events():
        loop = asyncio.get_running_loop()
        # Run streaming agent in executor, collect events via queue
        queue = asyncio.Queue()
        
        def runner():
            try:
                for event in run_agent_loop_streaming(
                    task=user_message,
                    session_id=session_id,
                    model_name=used_model,
                    tools=get_all_tools(),
                    abort_event=abort_event,
                    system_prompt=_load_system_prompt(),
                    max_iterations=1000,  # 迭代上限1000（按用户要求恢复）
                ):
                    # Put event into queue for the async generator to pick up
                    _safe_coro_call(loop, queue, event)
                # Signal done
                _safe_coro_call(loop, queue, None)
            except Exception as e:
                logger.error(f"Streaming agent failed: {e}")
                _safe_coro_call(loop, queue, {"type": "error", "message": str(e)})
                _safe_coro_call(loop, queue, None)
        
        # Start runner in thread pool
        loop.run_in_executor(_get_executor(), runner)
        
        # Track full result for saving to history
        full_result = ""
        final_data = {}
        
        _stream_start = time.monotonic()
        _STREAM_MAX_SECONDS = 3600  # 🛡️ SSE 流总时长上限：1 小时强制中止（防客户端断开检测失效导致后台空转）
        while True:
            # ⏰ 流超时强制中止（兜底：is_disconnected 在某些浏览器场景不可靠）
            if time.monotonic() - _stream_start > _STREAM_MAX_SECONDS:
                abort_event.set("timeout")
                logger.warning(f"⏰ [API] SSE 流超时({_STREAM_MAX_SECONDS}s)，强制中止会话 {session_id}")
                break
            # \U0001f514 客户端断开（关窗/点终止）→ 自动中止服务端任务，防止后台空转
            try:
                if await request.is_disconnected():
                    abort_event.set("disconnected")
                    logger.info(f"\u23f9 [API] 客户端断开连接，中止会话 {session_id}")
                    break
            except Exception:
                pass
            try:
                # 1s 轮询等待：长任务期间 agent 可能长时间不产生事件，
                # 若一次阻塞 600s，则客户端点中止/关页面后服务端无法及时停止，线程被长期占用
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # 轮询超时：交给循环顶部重新检查 is_disconnected / abort_event，然后继续等待
                if abort_event.is_set():
                    break
                continue
            
            if event is None:
                break
            
            # Track text chunks for final result
            if event.get("type") == "text_chunk":
                full_result += event.get("content", "")
            elif event.get("type") == "done":
                final_data = event
                full_result = event.get("result", full_result)
                # 标记生成该回复的模型
                final_data["model"] = used_model
                # Save final result
                save_message(session_id, "assistant", full_result, model=used_model)
            
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # Final done event if not already sent
        if final_data:
            final_data["session_id"] = session_id
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/history")
async def chat_history(session_id: str = None):
    """获取对话历史"""
    if session_id:
        messages = get_session_messages(session_id)
        return {"session_id": session_id, "messages": messages}
    else:
        sessions = get_recent_sessions()
        return {"sessions": sessions}


@router.delete("/session/{session_id}")
async def delete_chat_session(session_id: str):
    """删除对话会话"""
    delete_session(session_id)
    return {"success": True, "message": f"已删除会话: {session_id}"}


@router.post("/abort/{session_id}")
async def abort_chat(session_id: str):
    """中止正在执行的 AI 任务"""
    if session_id in _abort_flags:
        _abort_flags[session_id].set("user_aborted")
        logger.info(f"⏹ [API] 用户中止会话 {session_id}")
        return {"success": True, "message": "已发送中止信号"}
    return {"success": False, "message": "没有正在执行的任务"}


def _safe_loop_call(loop, fn, *args):
    """在线程中安全回调事件循环：循环已关闭时静默忽略（防止 cannot schedule new futures）"""
    try:
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(fn, *args)
    except Exception:
        pass


def _safe_coro_call(loop, queue, event):
    """线程中安全投递事件到异步队列：循环已关闭时静默忽略"""
    try:
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(queue.put(event), loop).result(timeout=5)
    except Exception:
        pass


# ===== 语音朗读开关（读写 app_settings，与桌面版 voice_mode/voice_gender 一致）=====

class VoiceSettings(BaseModel):
    mode: Optional[bool] = None
    gender: Optional[str] = None


def _app_settings_db() -> str:
    from ...database.db import _get_data_dir
    return str(_get_data_dir() / "games.db")


def _get_voice_setting(key: str, default: str = "") -> str:
    import sqlite3
    try:
        con = sqlite3.connect(_app_settings_db(), timeout=3)
        try:
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute("SELECT value FROM app_settings WHERE key=?", (key,))
            row = cur.fetchone()
            return str(row[0]) if row else default
        finally:
            con.close()
    except Exception as e:
        logger.warning(f"读取语音设置 {key} 失败: {e}")
        return default


def _set_voice_setting(key: str, value: str) -> bool:
    import sqlite3
    try:
        con = sqlite3.connect(_app_settings_db(), timeout=3)
        try:
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(
                "INSERT INTO app_settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            con.commit()
        finally:
            con.close()
        return True
    except Exception as e:
        logger.warning(f"写入语音设置 {key} 失败: {e}")
        return False


def _sync_tts_gender() -> None:
    """将数据库里的 voice_gender 同步到 TTS 引擎内存（否则切换性别不生效）"""
    try:
        g = _get_voice_setting("voice_gender", "female").lower().strip()
        if g not in ("female", "male"):
            g = "female"
        from data.plugins.tts_piper.tools import tts_set_gender
        tts_set_gender(g)
    except Exception as e:
        logger.warning(f"同步 TTS 性别失败: {e}")


def _tts_engine_now() -> str:
    """返回 TTS 引擎当前实际使用的性别（用于前端展示/诊断）"""
    try:
        from data.plugins.tts_piper.tools import tts_get_gender
        return tts_get_gender().get("gender", "")
    except Exception:
        return ""


@router.get("/voice")
async def get_voice_settings():
    """读取语音朗读开关/性别（与桌面版共用 app_settings.voice_mode / voice_gender）"""
    _sync_tts_gender()
    return {
        "mode": _get_voice_setting("voice_mode", "false").lower() == "true",
        "gender": _get_voice_setting("voice_gender", "male"),
        "engine": _tts_engine_now(),
    }


@router.post("/voice")
async def set_voice_settings(req: VoiceSettings):
    """更新语音朗读开关/性别"""
    if req.mode is not None:
        _set_voice_setting("voice_mode", "true" if req.mode else "false")
    if req.gender:
        _set_voice_setting("voice_gender", req.gender)
    _sync_tts_gender()
    return {
        "mode": _get_voice_setting("voice_mode", "false").lower() == "true",
        "gender": _get_voice_setting("voice_gender", "male"),
        "engine": _tts_engine_now(),
    }

