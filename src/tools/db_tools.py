"""
数据库操作工具 — 去重检查、版本比较、资源查询、资源删除
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
def db_save_resource(
    resource_type: str = "game",
    title: str = "",
    source_url: str = "",
    source_site: str = "",
    source_id: str = "",
    category: str = "",
    version: str = "",
    platform: str = "",
    language: str = "",
    file_size: str = "",
    intro: str = "",
    tags: str = "",
    status: str = "pending",
) -> str:
    """保存或更新资源"""
    session = get_session()
    try:
        # 查重：按 source_site + source_id
        existing = None
        if source_site and source_id:
            existing = session.query(Resource).filter(
                Resource.source_site == source_site,
                Resource.source_id == source_id,
            ).first()

        if existing:
            # 更新
            existing.title = title or existing.title
            existing.source_url = source_url or existing.source_url
            existing.category = category or existing.category
            existing.version = version or existing.version
            existing.platform = platform or existing.platform
            existing.language = language or existing.language
            existing.file_size = file_size or existing.file_size
            existing.intro = intro or existing.intro
            if tags:
                import json
                existing.tags = json.loads(tags) if isinstance(tags, str) else tags
            existing.status = status or existing.status
            session.commit()
            return f"✅ 已更新: {existing.title} (ID={existing.id})"
        else:
            # 新建
            import json
            resource = Resource(
                resource_type=resource_type,
                title=title,
                source_url=source_url,
                source_site=source_site,
                source_id=source_id,
                category=category,
                version=version,
                platform=platform,
                language=language,
                file_size=file_size,
                intro=intro,
                tags=json.loads(tags) if isinstance(tags, str) and tags else [],
                status=status,
            )
            session.add(resource)
            session.commit()
            return f"✅ 已创建: {title} (ID={resource.id})"
    except Exception as e:
        session.rollback()
        logger.error(f"保存资源失败: {e}")
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
def db_query_resources(
    resource_type: str = "",
    status: str = "",
    keyword: str = "",
    limit: int = 20,
    offset: int = 0,
) -> str:
    """查询资源列表"""
    session = get_session()
    try:
        query = session.query(Resource)
        if resource_type:
            query = query.filter(Resource.resource_type == resource_type)
        if status:
            query = query.filter(Resource.status == status)
        if keyword:
            query = query.filter(Resource.title.contains(keyword))

        total = query.count()
        rows = query.order_by(Resource.created_at.desc()).offset(offset).limit(limit).all()

        if not rows:
            return "📭 没有符合条件的资源"

        lines = [f"📋 资源列表 (共 {total} 条，显示 {len(rows)} 条):"]
        for r in rows:
            lines.append(
                f"  [{r.id}] {r.title} | {r.resource_type} | {r.status} | "
                f"{r.version or '-'} | {r.created_at.strftime('%Y-%m-%d') if r.created_at else '-'}"
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
    """检查版本"""
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


@register_tool(
    name="db_delete_resource",
    description="删除资源及其关联的任务日志。支持按ID删除或按标题模糊匹配删除（唯一匹配时）。需要 confirm=True 确认。",
    parameters={
        "type": "object",
        "properties": {
            "resource_id": {"type": "integer", "description": "资源 ID（与 title 二选一）"},
            "title": {"type": "string", "description": "资源标题（模糊匹配，与 resource_id 二选一）"},
            "confirm": {"type": "boolean", "description": "必须显式确认删除，防止误操作", "default": False},
        },
        "required": ["confirm"]
    },
    category="db",
    requires_db=True,
)
def db_delete_resource(resource_id: int = None, title: str = "", confirm: bool = False) -> str:
    """删除资源及其关联任务日志"""
    if not confirm:
        return "⚠️ 请设置 confirm=True 确认删除操作"

    session = get_session()
    try:
        if resource_id:
            resource = session.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                return f"❌ 未找到 ID={resource_id} 的资源"
        elif title.strip():
            resources = session.query(Resource).filter(
                Resource.title.contains(title.strip())
            ).all()
            if not resources:
                return f"❌ 未找到标题包含「{title}」的资源"
            if len(resources) > 1:
                lines = [f"⚠️ 找到 {len(resources)} 条匹配资源，请用 resource_id 精确指定："]
                for r in resources:
                    lines.append(f"  ID={r.id}: {r.title} [{r.resource_type}] {r.status}")
                return "\n".join(lines)
            resource = resources[0]
        else:
            return "❌ 请提供 resource_id 或 title"

        rid = resource.id
        rtitle = resource.title

        # 删除关联任务日志
        deleted_logs = session.query(TaskLog).filter(TaskLog.resource_id == rid).delete()
        # 删除资源
        session.delete(resource)
        session.commit()

        logger.info(f"🗑️ 已删除资源: {rtitle} (ID={rid}), 关联日志 {deleted_logs} 条")
        return f"✅ 已删除: {rtitle} (ID={rid})\n  同时删除了 {deleted_logs} 条关联任务日志"
    except Exception as e:
        session.rollback()
        logger.error(f"删除资源失败: {e}")
        return f"❌ 删除失败: {e}"
    finally:
        session.close()
