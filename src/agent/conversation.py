"""
对话历史管理 — 持久化 + 检索
"""
import uuid
from datetime import datetime

from loguru import logger

from ..database.db import get_session, ConversationHistory


def create_session() -> str:
    """创建新对话会话"""
    return str(uuid.uuid4())[:8]


def save_message(session_id: str, role: str, content: str, tool_name: str = ""):
    """保存对话消息到数据库"""
    session = get_session()
    try:
        msg = ConversationHistory(
            session_id=session_id,
            role=role,
            content=content,
            tool_name=tool_name,
        )
        session.add(msg)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"保存对话失败: {e}")
    finally:
        session.close()


def get_session_messages(session_id: str, limit: int = 100) -> list:
    """获取会话的所有消息"""
    session = get_session()
    try:
        messages = session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).order_by(ConversationHistory.created_at.desc()).limit(limit).all()
        # desc 取最近 N 条，再反转回升序（时间正序）
        messages_list = [m.to_dict() for m in messages]
        messages_list.reverse()
        return messages_list
    finally:
        session.close()


def get_recent_sessions(limit: int = 20) -> list:
    """获取最近的会话列表"""
    session = get_session()
    try:
        # 按 session_id 分组取最新
        from sqlalchemy import func, desc
        subq = session.query(
            ConversationHistory.session_id,
            func.max(ConversationHistory.created_at).label("last_activity"),
        ).group_by(ConversationHistory.session_id).order_by(
            desc("last_activity")
        ).limit(limit).all()

        result = []
        for sid, last_act in subq:
            # 取该 session 的第一条用户消息作为标题
            first_msg = session.query(ConversationHistory).filter(
                ConversationHistory.session_id == sid,
                ConversationHistory.role == "user",
            ).order_by(ConversationHistory.created_at.asc()).first()

            msg_count = session.query(ConversationHistory).filter(
                ConversationHistory.session_id == sid,
            ).count()

            title = first_msg.content[:50] if first_msg else "(空)"
            result.append({
                "session_id": sid,
                "title": title,
                "message_count": msg_count,
                "last_activity": str(last_act),
            })

        return result
    finally:
        session.close()


def delete_session(session_id: str):
    """删除会话"""
    session = get_session()
    try:
        session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).delete()
        session.commit()
        logger.info(f"🗑️ 已删除会话: {session_id}")
    finally:
        session.close()
