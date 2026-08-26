"""
核心文件清单模板 — 供 integrity.py 的 IntegrityChecker.generate_manifest() 使用
详见架构文档 §24.3
"""

# 核心代码文件（critical 级别）
CORE_FILES = [
    # 入口
    "main.py",

    # Agent 核心
    "src/agent/agent_loop.py",
    "src/agent/model_manager.py",
    "src/agent/context_manager.py",
    "src/agent/prompts.py",
    "src/agent/conversation.py",

    # 工具注册中心
    "src/tools/registry.py",

    # 工具模块
    "src/tools/browser_tools.py",
    "src/tools/download_tools.py",
    "src/tools/db_tools.py",
    "src/tools/content_tools.py",
    "src/tools/oss_tools.py",
    "src/tools/image_tools.py",
    "src/tools/file_tools.py",
    "src/tools/publish_tools.py",
    "src/tools/self_modify_tools.py",
    "src/tools/monitor_tools.py",

    # 数据库
    "src/database/db.py",

    # 配置
    "src/config/loader.py",

    # 流水线
    "src/pipeline/pipeline.py",
    "src/pipeline/task_queue.py",

    # 调度
    "src/scheduler/scheduler.py",
    "src/scheduler/jobs.py",
    "src/scheduler/daemon.py",

    # Web
    "src/web/server.py",
    "src/web/ws.py",

    # CLI
    "src/cli.py",

    # 安全
    "src/security/integrity.py",
    "src/security/manifest_template.py",

    # 工具模块
    "src/utils/logger.py",
    "src/utils/helpers.py",
    "src/utils/retry.py",
    "src/utils/crypto.py",
]

# 标准级别文件 (tools/pipeline — AI 可修改)
STANDARD_FILES = [
    # 这些文件 AI 自改进可能修改
]

# 宽松级别文件 (web/static — 前端资源)
LOOSE_FILES = [
    "src/web/templates/index.html",
    "src/web/static/css/app.css",
    "src/web/static/js/app.js",
    "src/web/static/js/router.js",
    "src/web/static/js/store.js",
    "src/web/static/js/components/Sidebar.js",
    "src/web/static/js/components/Dashboard.js",
    "src/web/static/js/components/ChatPanel.js",
    "src/web/static/js/components/ResourceTable.js",
    "src/web/static/js/components/TaskMonitor.js",
    "src/web/static/js/components/SourceManager.js",
    "src/web/static/js/components/Analytics.js",
    "src/web/static/js/components/Settings.js",
]


def get_files_by_level(level: str) -> list:
    """根据保护级别获取文件列表"""
    if level == "critical":
        return CORE_FILES
    elif level == "standard":
        return CORE_FILES + STANDARD_FILES
    elif level == "loose":
        return CORE_FILES + STANDARD_FILES + LOOSE_FILES
    elif level == "full":
        return CORE_FILES + STANDARD_FILES + LOOSE_FILES
    return CORE_FILES
