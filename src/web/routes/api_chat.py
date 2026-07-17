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
import asyncio
import concurrent.futures

from ...agent.agent_loop import run_agent_loop
from ...agent.conversation import (
    create_session, save_message, get_session_messages,
    get_recent_sessions, delete_session,
)
from loguru import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 专用线程池，避免阻塞 FastAPI 事件循环（懒加载 + 自动重创建）
_chat_executor = None

def _get_executor():
    """获取（或重建）线程池"""
    global _chat_executor
    if _chat_executor is None or _chat_executor._shutdown:
        _chat_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    return _chat_executor


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


@router.post("/send")
async def send_message(req: ChatRequest):
    """发送对话消息"""
    session_id = req.session_id or create_session()

    # 保存用户消息
    save_message(session_id, "user", req.message)

    try:
        # 在线程池中运行 Agent 循环，避免阻塞 FastAPI 事件循环
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _get_executor(),
            lambda: run_agent_loop(
                task=req.message,
                session_id=session_id,
                model_name=req.model,
            )
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
    except Exception as e:
        logger.error(f"对话失败: {e}")
        save_message(session_id, "assistant", f"❌ {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
