"""
源站管理 API
GET    /api/sources        — 源站列表
POST   /api/sources        — 添加源站
PUT    /api/sources/{id}   — 更新源站
DELETE /api/sources/{id}   — 删除源站
POST   /api/sources/{id}/crawl — 立即爬取
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...database.db import get_session, SourceSite
from ...scheduler.jobs import crawl_source
from loguru import logger

router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str
    url: str
    site_type: str = "game"
    need_login: bool = False
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None
    crawl_interval: int = 360
    notes: Optional[str] = None


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    site_type: Optional[str] = None
    need_login: Optional[bool] = None
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None
    enabled: Optional[bool] = None
    crawl_interval: Optional[int] = None
    notes: Optional[str] = None


@router.get("")
async def list_sources():
    """获取源站列表（纯数据库读取，不再合并 config.yaml）"""
    session = get_session()
    try:
        db_sources = session.query(SourceSite).order_by(SourceSite.name).all()
        result = [s.to_dict() for s in db_sources]
    finally:
        session.close()
    return {"sources": result}


@router.post("")
async def create_source(source: SourceCreate):
    """添加新源站"""
    session = get_session()
    try:
        # 检查同名源站
        existing = session.query(SourceSite).filter(SourceSite.name == source.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"源站已存在: {source.name}")
        
        site = SourceSite(
            name=source.name,
            url=source.url,
            site_type=source.site_type,
            need_login=1 if source.need_login else 0,
            login_url=source.login_url,
            login_username=source.login_username,
            login_password=source.login_password,
            crawl_interval=source.crawl_interval,
            notes=source.notes,
        )
        session.add(site)
        session.commit()
        session.refresh(site)
        logger.info(f"➕ 源站已添加: {site.name}")
        return {"success": True, "data": site.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.put("/{source_id}")
async def update_source(source_id: int, source: SourceUpdate):
    """更新源站"""
    session = get_session()
    try:
        site = session.query(SourceSite).filter(SourceSite.id == source_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="源站不存在")
        
        update_data = source.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key in ("need_login",):
                setattr(site, key, 1 if value else 0)
            else:
                setattr(site, key, value)
        
        session.commit()
        session.refresh(site)
        logger.info(f"✏️ 源站已更新: {site.name}")
        return {"success": True, "data": site.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/{source_id}")
async def delete_source(source_id: int):
    """删除源站"""
    session = get_session()
    try:
        site = session.query(SourceSite).filter(SourceSite.id == source_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="源站不存在")
        name = site.name
        session.delete(site)
        session.commit()
        logger.info(f"🗑️ 源站已删除: {name}")
        return {"success": True, "message": f"已删除: {name}"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/{source_id}/crawl")
async def trigger_crawl(source_id: int):
    """手动触发源站爬取"""
    session = get_session()
    try:
        site = session.query(SourceSite).filter(SourceSite.id == source_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="源站不存在")
        if not site.enabled:
            raise HTTPException(status_code=400, detail="源站已禁用")
        
        from ...core.pipeline.task_queue import get_task_queue, TaskPriority
        tq = get_task_queue()
        task_id = tq.submit_function(
            func=crawl_source,
            name=f"爬取 {site.name}",
            priority=TaskPriority.HIGH,
        )

        return {"success": True, "task_id": task_id, "message": f"已提交爬取任务: {site.name}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
