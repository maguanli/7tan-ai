"""
工具注册中心 — 统一管理和注册 AI 可调用的工具
"""
from dataclasses import dataclass, field
from typing import Any, Callable

from loguru import logger


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: dict
    function: Callable
    category: str = "misc"       # browser/file/oss/db/image/content/publish/self_modify/monitor
    dangerous: bool = False
    requires_browser: bool = False
    requires_db: bool = False


# 全局注册表
TOOL_REGISTRY: dict[str, Tool] = {}


def register_tool(
    name: str = None,
    description: str = "",
    parameters: dict = None,
    category: str = "misc",
    dangerous: bool = False,
    requires_browser: bool = False,
    requires_db: bool = False,
):
    """
    工具注册装饰器

    用法一: 装饰函数
        @register_tool(name="download", description="...", parameters={...})
        def download(url): ...

    用法二: 装饰 Tool 子类
        @register_tool
        class MyTool(Tool): ...
    """
    def decorator(target):
        if isinstance(target, type):
            instance = target()
            tool = Tool(
                name=instance.name,
                description=instance.description,
                parameters=instance.parameters,
                function=instance.run if hasattr(instance, "run") else instance.__call__,
                category=getattr(instance, "category", category),
                dangerous=getattr(instance, "dangerous", dangerous),
                requires_browser=getattr(instance, "requires_browser", requires_browser),
                requires_db=getattr(instance, "requires_db", requires_db),
            )
        else:
            tool = Tool(
                name=name or target.__name__,
                description=description,
                parameters=parameters or {"type": "object", "properties": {}, "required": []},
                function=target,
                category=category,
                dangerous=dangerous,
                requires_browser=requires_browser,
                requires_db=requires_db,
            )
        TOOL_REGISTRY[tool.name] = tool
        logger.debug(f"🔧 注册工具: {tool.name} ({tool.category})")
        return target
    return decorator


def get_all_tools() -> list[dict]:
    """返回 OpenAI 兼容的 tools 数组"""
    result = []
    for t in TOOL_REGISTRY.values():
        # 兼容插件可能注册 dict 而不是 ToolDefinition
        if not hasattr(t, 'name'):
            logger.warning(f"⚠️ TOOL_REGISTRY 中混入 dict 而不是 ToolDefinition: {t}")
            name = t.get("name", "unknown")
            desc = t.get("description", "")
            params = t.get("parameters", {})
        result.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": params,
            }
        })
    return result


def get_tool(name: str) -> Tool:
    """根据名称获取工具"""
    return TOOL_REGISTRY.get(name)


def execute_tool(name: str, args: dict) -> str:
    """执行工具并返回结果字符串"""
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return f"❌ 未知工具: {name}"

    try:
        if tool.dangerous:
            logger.warning(f"⚠️ 执行危险工具: {name} ({args})")
        result = tool.function(**args)
        return str(result) if result is not None else "✅ 完成"
    except Exception as e:
        logger.error(f"❌ 工具执行失败 {name}: {e}")
        return f"❌ 工具执行失败: {e}"
