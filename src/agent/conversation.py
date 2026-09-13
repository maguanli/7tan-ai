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


def save_message(session_id: str, role: str, content: str, tool_name: str = "", model: str = ""):
    """保存对话消息到数据库

    Args:
        session_id: 会话 ID
        role: 'user' | 'assistant' | 'tool'
        content: 消息内容
        tool_name: 工具名（tool 消息用）
        model: 生成该消息的 AI 模型名（assistant 消息用）
    """
    session = get_session()
    try:
        msg = ConversationHistory(
            session_id=session_id,
            role=role,
            content=content,
            tool_name=tool_name,
            model=model,
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
    """获取最近的会话列表（单条 SQL，避免 N+1 问题，性能提升 ~40x）"""
    session = get_session()
    try:
        from sqlalchemy import text

        # 一条 SQL：JOIN 子查询，同时获取 last_activity / title / message_count
        # 原来需要 1 + 20*2 = 41 条 SQL，现在只需 1 条
        rows = session.execute(text("""
            SELECT
                s.session_id,
                s.last_activity,
                COALESCE(t.title, '(空)') AS title,
                COALESCE(c.cnt, 0) AS message_count
            FROM (
                SELECT
                    session_id,
                    MAX(created_at) AS last_activity
                FROM conversation_history
                GROUP BY session_id
                ORDER BY last_activity DESC
                LIMIT :limit
            ) s
            LEFT JOIN (
                SELECT session_id, content AS title
                FROM conversation_history
                WHERE role = 'user'
                AND id IN (
                    SELECT MIN(id)
                    FROM conversation_history
                    WHERE role = 'user'
                    GROUP BY session_id
                )
            ) t ON s.session_id = t.session_id
            LEFT JOIN (
                SELECT session_id, COUNT(*) AS cnt
                FROM conversation_history
                GROUP BY session_id
            ) c ON s.session_id = c.session_id
            ORDER BY s.last_activity DESC
        """), {"limit": limit}).fetchall()

        return [
            {
                "session_id": row.session_id,
                "title": (row.title[:50] if row.title and row.title != "(空)" else row.title),
                "message_count": row.message_count,
                "last_activity": str(row.last_activity),
            }
            for row in rows
        ]
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
