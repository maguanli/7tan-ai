"""
对话 API — 支持 SSE 流式响应
POST /api/chat/send    — 发送消息
GET  /api/chat/history — 获取历史
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import threading
import asyncio

from ...agent.agent_loop import run_agent_loop, run_agent_loop_streaming
from ...tools.registry import get_all_tools
from ... import tools as _tools  # noqa: F401 触发 @register_tool 装饰器
from ...agent.conversation import (
    create_session, save_message, get_session_messages,
    get_recent_sessions, delete_session,
)
from loguru import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])

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


class ChatResponse(BaseModel):
    session_id: str
    success: bool
    result: str
    cost: float = 0
    iterations: int = 0


def _load_system_prompt() -> str:
    """加载系统提示词，fallback 到内置默认"""
    try:
        from pathlib import Path
        prompt_path = Path("data/prompts/system.txt")
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""  # 空字符串表示无系统提示词，agent_loop 会跳过


@router.post("/send")
async def send_message(req: ChatRequest):
    """发送对话消息"""
    session_id = req.session_id or create_session()
    system_prompt = _load_system_prompt()

    # 保存用户消息
    save_message(session_id, "user", req.message)

    # 创建中止标志（供 abort 端点和 agent_loop 检查）
    abort_event = threading.Event()
    _abort_flags[session_id] = abort_event

    try:
        # 在线程中运行 Agent（threading.Thread，避免 ThreadPoolExecutor 与 PyQt6 冲突）
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def _run_agent():
            try:
                result = run_agent_loop(
                    task=req.message,
                    session_id=session_id,
                    model_name=req.model,
                    tools=get_all_tools(),
                    abort_event=abort_event,
                    system_prompt=system_prompt,
                )
                loop.call_soon_threadsafe(future.set_result, result)
            except Exception as e:
                loop.call_soon_threadsafe(future.set_exception, e)

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

        # 保存 AI 回复
        save_message(session_id, "assistant", result.get("result", ""))

        return ChatResponse(
            session_id=session_id,
            success=result["success"],
            result=result["result"],
            cost=result.get("cost", 0),
            iterations=result.get("iterations", 0),
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
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="chat-stream")
    return _executor


@router.post("/send/stream")
async def send_message_stream(req: ChatRequest):
    """SSE 流式发送对话消息 — 逐步返回思考过程和结果"""
    session_id = req.session_id or create_session()
    save_message(session_id, "user", req.message)
    
    # 创建中止标志
    abort_event = threading.Event()
    _abort_flags[session_id] = abort_event
    
    async def event_generator():
        loop = asyncio.get_running_loop()
        # Run streaming agent in executor, collect events via queue
        queue = asyncio.Queue()
        
        def runner():
            try:
                for event in run_agent_loop_streaming(
                    task=req.message,
                    session_id=session_id,
                    model_name=req.model,
                    tools=get_all_tools(),
                    abort_event=abort_event,
                    system_prompt=_load_system_prompt(),
                ):
                    # Put event into queue for the async generator to pick up
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()
                # Signal done
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()
            except Exception as e:
                logger.error(f"Streaming agent failed: {e}")
                asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "message": str(e)}), loop).result()
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()
        
        # Start runner in thread pool
        loop.run_in_executor(_get_executor(), runner)
        
        # Track full result for saving to history
        full_result = ""
        final_data = {}
        
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Timeout - 300s'})}\n\n"
                break
            
            if event is None:
                break
            
            # Track text chunks for final result
            if event.get("type") == "text_chunk":
                full_result += event.get("content", "")
            elif event.get("type") == "done":
                final_data = event
                full_result = event.get("result", full_result)
                # Save final result
                save_message(session_id, "assistant", full_result)
            
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # Final done event if not already sent
        if final_data:
            final_data["session_id"] = session_id
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
    
    try:
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    finally:
        _abort_flags.pop(session_id, None)


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
        _abort_flags[session_id].set()
        logger.info(f"⏹ [API] 用户中止会话 {session_id}")
        return {"success": True, "message": "已发送中止信号"}
    return {"success": False, "message": "没有正在执行的任务"}
