"""
项目 API — VS Code 扩展集成
POST /api/project/index — 接收项目索引数据
POST /api/project/open  — 在 7Tan 中打开项目
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

router = APIRouter(prefix="/api/project", tags=["project"])

# 存储最近索引的项目信息
_recent_projects = {}


class ProjectIndexRequest(BaseModel):
    root_path: str
    total_files: int = 0
    total_size: int = 0
    project_type: str = "未知"
    languages: List[str] = []
    source_count: int = 0
    config_count: int = 0
    resource_count: int = 0


class ProjectOpenRequest(BaseModel):
    path: str


@router.post("/index")
async def index_project(req: ProjectIndexRequest):
    """接收 VS Code 扩展提交的项目索引数据"""
    _recent_projects[req.root_path] = {
        "total_files": req.total_files,
        "total_size": req.total_size,
        "project_type": req.project_type,
        "languages": req.languages,
        "source_count": req.source_count,
        "config_count": req.config_count,
        "resource_count": req.resource_count,
    }
    logger.info(f"📊 项目已索引: {req.root_path} ({req.project_type}, {req.total_files} 文件)")
    return {"success": True, "message": f"已索引 {req.total_files} 个文件"}


@router.post("/open")
async def open_project(req: ProjectOpenRequest):
    """在 7Tan 中打开项目"""
    import os
    if not os.path.exists(req.path):
        return {"success": False, "message": f"路径不存在: {req.path}"}

    logger.info(f"📂 在 7Tan 中打开项目: {req.path}")
    
    # 更新数据库中的当前工作项目
    info = _recent_projects.get(req.path, {})
    return {
        "success": True,
        "path": req.path,
        "project_type": info.get("project_type", "未知"),
        "languages": info.get("languages", []),
    }


@router.get("/info")
async def project_info(path: str = None):
    """获取项目信息"""
    if path and path in _recent_projects:
        return {"success": True, "data": _recent_projects[path]}
    return {"success": True, "data": list(_recent_projects.keys())}
