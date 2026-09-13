"""
任务查询/控制 API
GET  /api/tasks         — 所有任务状态
GET  /api/tasks/active  — 活跃任务
POST /api/tasks/{id}/cancel — 取消任务
"""
from fastapi import APIRouter, HTTPException

from ...pipeline.task_queue import get_task_queue
from ...database.db import get_session, TaskLog

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks():
    """获取所有任务（含历史）"""
    tq = get_task_queue()
    return {
        "active": tq.get_active_tasks(),
        "queued": tq.get_queued_tasks(),
        "all": tq.get_all_tasks(),
        "stats": {
            "active_count": tq.get_active_count(),
            "queued_count": tq.get_queue_size(),
        },
    }


@router.get("/active")
async def active_tasks():
    """获取活跃任务"""
    tq = get_task_queue()
    return {"tasks": tq.get_active_tasks()}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    tq = get_task_queue()
    if tq.cancel(task_id):
        return {"success": True, "message": f"任务 {task_id} 已取消"}
    raise HTTPException(status_code=404, detail="任务不存在或无法取消")


@router.get("/logs")
async def task_logs(resource_id: int = None, limit: int = 50):
    """获取任务日志"""
    session = get_session()
    try:
        query = session.query(TaskLog)
        if resource_id:
            query = query.filter(TaskLog.resource_id == resource_id)
        rows = query.order_by(TaskLog.started_at.desc()).limit(limit).all()
        return {"logs": [r.to_dict() for r in rows]}
    finally:
        session.close()
