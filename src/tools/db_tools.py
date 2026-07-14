"""
数据库操作工具 — 去重检查、版本比较、资源查询
"""
from datetime import datetime

from loguru import logger

from .registry import register_tool
from ..database.db import get_session, Resource, TaskLog, SourceSite, ConversationHistory


@register_tool(
    name="db_check_duplicate",
    description="检查资源是否已存在（按源站ID去重）。返回 None 表示新资源，否则返回已有记录。",
    parameters={
        "type": "object",
        "properties": {
            "source_site": {"type": "string", "description": "源站标识"},
            "source_id": {"type": "string", "description": "源站唯一 ID"},
            "title": {"type": "string", "description": "资源标题"},
        },
        "required": ["source_site", "source_id"]
    },
    category="db",
    requires_db=True,
)
def db_check_duplicate(source_site: str, source_id: str, title: str = "") -> str:
    """检查资源是否已存在"""
    session = get_session()
    try:
        existing = session.query(Resource).filter(
            Resource.source_site == source_site,
            Resource.source_id == source_id,
        ).first()

        if existing:
            return f"🔁 资源已存在:\n  ID: {existing.id}\n  标题: {existing.title}\n  版本: {existing.version}\n  状态: {existing.status}"
        else:
            return f"✅ 新资源: {title}"
    finally:
        session.close()


@register_tool(
    name="db_save_resource",
    description="保存或更新资源信息到数据库。返回资源 ID。",
    parameters={
        "type": "object",
        "properties": {
            "resource_type": {"type": "string", "description": "'game' 或 'software'", "default": "game"},
            "title": {"type": "string", "description": "资源标题"},
            "source_url": {"type": "string", "description": "源站 URL"},
            "source_site": {"type": "string", "description": "源站标识"},
            "source_id": {"type": "string", "description": "源站唯一 ID"},
            "category": {"type": "string", "description": "分类"},
            "version": {"type": "string", "description": "版本号"},
            "platform": {"type": "string", "description": "平台"},
            "language": {"type": "string", "description": "语言"},
            "file_size": {"type": "string", "description": "文件大小"},
            "intro": {"type": "string", "description": "简介"},
            "tags": {"type": "string", "description": "标签(JSON数组)"},
            "status": {"type": "string", "description": "状态", "default": "pending"},
        },
        "required": ["title", "source_url"]
    },
    category="db",
    requires_db=True,
)
def db_save_resource(**kwargs) -> str:
    """保存资源到数据库"""
    import json as _json
    session = get_session()
    try:
        # 去重
        source_site = kwargs.get("source_site", "")
        source_id = kwargs.get("source_id", "")
        if source_site and source_id:
            existing = session.query(Resource).filter(
                Resource.source_site == source_site,
                Resource.source_id == source_id,
            ).first()
            if existing:
                # 更新
                for key, val in kwargs.items():
                    if key == "tags" and isinstance(val, str):
                        try:
                            val = _json.loads(val)
                        except Exception:
                            pass
                    if hasattr(existing, key) and val is not None:
                        setattr(existing, key, val)
                existing.updated_at = datetime.now()
                session.commit()
                return f"✅ 资源已更新: ID={existing.id}"

        # 新建
        tags_val = kwargs.pop("tags", None)
        resource = Resource(**kwargs)
        if tags_val:
            if isinstance(tags_val, str):
                try:
                    resource.tags = _json.loads(tags_val)
                except Exception:
                    resource.tags = [tags_val]
            else:
                resource.tags = tags_val

        session.add(resource)
        session.commit()
        logger.info(f"💾 资源已保存: ID={resource.id}, 标题={resource.title}")
        return f"✅ 资源已保存: ID={resource.id}"
    except Exception as e:
        session.rollback()
        return f"❌ 保存失败: {e}"
    finally:
        session.close()


@register_tool(
    name="db_query_resources",
    description="查询资源列表。可按类型、状态、标题过滤。",
    parameters={
        "type": "object",
        "properties": {
            "resource_type": {"type": "string", "description": "'game' / 'software' / 留空=全部"},
            "status": {"type": "string", "description": "状态过滤"},
            "keyword": {"type": "string", "description": "标题关键词搜索"},
            "limit": {"type": "integer", "description": "返回数量", "default": 20},
            "offset": {"type": "integer", "description": "偏移量", "default": 0},
        },
        "required": []
    },
    category="db",
    requires_db=True,
)
def db_query_resources(resource_type: str = None, status: str = None,
                       keyword: str = None, limit: int = 20, offset: int = 0) -> str:
    """查询资源列表"""
    session = get_session()
    try:
        q = session.query(Resource)
        if resource_type:
            q = q.filter(Resource.resource_type == resource_type)
        if status:
            q = q.filter(Resource.status == status)
        if keyword:
            q = q.filter(Resource.title.contains(keyword))

        total = q.count()
        rows = q.order_by(Resource.created_at.desc()).offset(offset).limit(limit).all()

        lines = [f"📦 资源列表 (共 {total} 个, 显示 {len(rows)} 个):\n"]
        for r in rows:
            size_str = r.file_size or "未知"
            status_icon = {"published": "✅", "pending": "⏳", "downloading": "🔄",
                           "failed": "❌", "rewriting": "✏️"}.get(r.status, "📌")
            type_icon = "🎮" if r.resource_type == "game" else "💻"
            lines.append(
                f"  {status_icon} [{r.id}] {type_icon} {r.title} "
                f"v{r.version or '?'} | {size_str} | {r.status}"
            )
        return "\n".join(lines)
    finally:
        session.close()


@register_tool(
    name="db_check_version",
    description="检查某资源是否已有更早版本。返回版本比较结果。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "资源标题"},
            "new_version": {"type": "string", "description": "新发现的版本号"},
            "source_site": {"type": "string", "description": "源站标识"},
        },
        "required": ["title", "new_version"]
    },
    category="db",
    requires_db=True,
)
def db_check_version(title: str, new_version: str, source_site: str = "") -> str:
    """版本比较"""
    session = get_session()
    try:
        existing = session.query(Resource).filter(
            Resource.title.contains(title.strip())
        ).order_by(Resource.created_at.desc()).first()

        if not existing:
            return f"✅ 新资源，无历史版本"

        old_version = existing.version or ""
        if old_version == new_version:
            return f"⚖️ 版本相同 ({new_version})，无需更新"
        elif new_version > old_version:
            return (
                f"🆕 新版本! {old_version} → {new_version}\n"
                f"  已有资源ID: {existing.id}\n"
                f"  标题: {existing.title}"
            )
        else:
            return f"📌 当前版本 ({new_version}) 不高于已有版本 ({old_version})"
    finally:
        session.close()


@register_tool(
    name="db_add_task_log",
    description="记录任务日志",
    parameters={
        "type": "object",
        "properties": {
            "resource_id": {"type": "integer", "description": "资源 ID"},
            "task_type": {"type": "string", "description": "browse/download/rewrite/upload/publish"},
            "status": {"type": "string", "description": "running/success/failed"},
            "message": {"type": "string", "description": "日志消息"},
        },
        "required": ["resource_id", "task_type", "status"]
    },
    category="db",
    requires_db=True,
)
def db_add_task_log(resource_id: int, task_type: str, status: str, message: str = "") -> str:
    """添加任务日志"""
    session = get_session()
    try:
        log = TaskLog(
            resource_id=resource_id,
            task_type=task_type,
            status=status,
            message=message,
            started_at=datetime.now() if status == "running" else None,
            finished_at=datetime.now() if status in ("success", "failed") else None,
        )
        session.add(log)
        session.commit()
        return f"✅ 日志已记录: {task_type} - {status}"
    finally:
        session.close()
