"""
路由模块 — 所有 REST API 路由
"""
from .api_resources import router as resources_router
from .api_tasks import router as tasks_router
from .api_sources import router as sources_router
from .api_stats import router as stats_router
from .api_settings import router as settings_router
from .api_chat import router as chat_router
from .api_project import router as project_router
from .api_terminal import router as terminal_router
from .api_update import router as update_router
from .api_code import router as code_router
from .api_license import router as license_router
from .api_adapt import router as adapt_router
from .api_mind import router as mind_router

__all__ = [
    "resources_router",
    "tasks_router",
    "sources_router",
    "stats_router",
    "settings_router",
    "chat_router",
    "project_router",
    "terminal_router",
    "update_router",
    "code_router",
    "license_router",
    "adapt_router",
    "mind_router",
]
