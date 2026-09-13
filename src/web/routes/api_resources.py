"""
资源 CRUD API — RESTful 接口
GET    /api/resources       — 列表（分页/筛选）
GET    /api/resources/{id}  — 详情
POST   /api/resources       — 创建
PUT    /api/resources/{id}  — 更新
DELETE /api/resources/{id}  — 删除
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ...database.db import get_session, Resource
from loguru import logger

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("")
async def list_resources(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    source_site: Optional[str] = None,
):
    """获取资源列表"""
    session = get_session()
    try:
        query = session.query(Resource)

        if resource_type:
            query = query.filter(Resource.resource_type == resource_type)
        if status:
            query = query.filter(Resource.status == status)
        if source_site:
            query = query.filter(Resource.source_site == source_site)
        if search:
            query = query.filter(Resource.title.contains(search))

        total = query.count()
        rows = query.order_by(Resource.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "resources": [r.to_dict() for r in rows],
        }
    finally:
        session.close()


@router.get("/{resource_id}")
async def get_resource(resource_id: int):
    """获取资源详情"""
    session = get_session()
    try:
        resource = session.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="资源不存在")
        return resource.to_dict()
    finally:
        session.close()


@router.delete("/{resource_id}")
async def delete_resource(resource_id: int):
    """删除资源"""
    session = get_session()
    try:
        resource = session.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="资源不存在")
        session.delete(resource)
        session.commit()
        logger.info(f"🗑️ 资源已删除: {resource.title} (ID={resource_id})")
        return {"success": True, "message": f"已删除: {resource.title}"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
