"""
统计数据 API
GET /api/stats/dashboard    — 仪表盘概览
GET /api/stats/publish      — 发布趋势
GET /api/stats/costs        — 费用统计
"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from sqlalchemy import func

from ...database.db import get_session, Resource, TaskLog, ConversationHistory
from ...tools.monitor_tools import get_cost_report, get_system_status

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/dashboard")
async def dashboard():
    """仪表盘概览数据 — §21.5 四张统计卡片"""
    session = get_session()
    try:
        # 已发布总数
        total_published = session.query(Resource).filter(
            Resource.status == "published"
        ).count()

        # 处理中
        in_progress = session.query(Resource).filter(
            Resource.status.in_(["downloading", "rewriting", "uploading", "pending"])
        ).count()

        # 本月新增
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        this_month = session.query(Resource).filter(
            Resource.created_at >= month_start
        ).count()

        # 今日费用
        cost_report = get_cost_report(days=1)
        today_cost = cost_report.get("total_cost", 0)

        # 成功率
        total = session.query(Resource).count()
        failed = session.query(Resource).filter(
            Resource.status == "failed"
        ).count()
        success_rate = round((1 - failed / total) * 100, 1) if total > 0 else 100

        # 系统状态
        system = get_system_status()

        return {
            "total_published": total_published,
            "in_progress": in_progress,
            "this_month_new": this_month,
            "today_cost": round(today_cost, 4),
            "success_rate": success_rate,
            "system": system,
        }
    finally:
        session.close()


@router.get("/publish")
async def publish_trend(days: int = Query(7, ge=1, le=90)):
    """发布趋势 — §21.5 折线图"""
    session = get_session()
    try:
        trend = []
        for i in range(days, 0, -1):
            date = datetime.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = date.replace(hour=23, minute=59, second=59)

            count = session.query(Resource).filter(
                Resource.status == "published",
                Resource.published_at >= day_start,
                Resource.published_at <= day_end,
            ).count()

            trend.append({
                "date": day_start.strftime("%m-%d"),
                "count": count,
            })

        return {"trend": trend}
    finally:
        session.close()


@router.get("/types")
async def resource_types():
    """资源类型分布 — §21.5 环形图"""
    session = get_session()
    try:
        game_count = session.query(Resource).filter(
            Resource.resource_type == "game"
        ).count()
        software_count = session.query(Resource).filter(
            Resource.resource_type == "software"
        ).count()

        return {
            "types": [
                {"name": "游戏", "value": game_count, "color": "#6366f1"},
                {"name": "软件", "value": software_count, "color": "#8b5cf6"},
            ],
        }
    finally:
        session.close()


@router.get("/costs")
async def cost_stats(days: int = Query(30, ge=1, le=365)):
    """费用统计"""
    report = get_cost_report(days=days)
    return report
