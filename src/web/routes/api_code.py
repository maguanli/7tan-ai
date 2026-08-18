"""
代码变更 API — AI 修改记录查看（网页版代码查看器）

GET /api/code/changes — 最近文件变更（含 unified diff）列表
"""
from fastapi import APIRouter, Query

from ...utils.code_change_bus import load_history
from loguru import logger

router = APIRouter(prefix="/api/code", tags=["code"])


@router.get("/changes")
async def code_changes(limit: int = Query(50, ge=1, le=300)):
    """读取 data/code_changes.jsonl 中的最近文件变更（新 → 旧）"""
    try:
        recs = load_history(limit=limit)  # 旧 → 新
        recs = list(reversed(recs))       # 新 → 旧，最新变更在最前
        return {"changes": recs, "total": len(recs)}
    except Exception as e:
        logger.error(f"读取代码变更历史失败: {e}")
        return {"changes": [], "total": 0, "error": str(e)}
