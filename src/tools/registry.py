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

# 已警告过的 dict 类型工具名（避免重复告警）
_warned_dict_tools: set = set()


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
            # 智能包装: 如果 parameters 缺少 type/properties，自动补全 JSON Schema
            params = parameters or {}
            if isinstance(params, dict) and "type" not in params:
                params = {"type": "object", "properties": params, "required": list(params.keys())}
            tool = Tool(
                name=name or target.__name__,
                description=description,
                parameters=params,
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
    for key, t in list(TOOL_REGISTRY.items()):
        # 兼容插件可能注册 dict 而不是 Tool（旧版本遗留问题）
        if hasattr(t, 'name'):
            name, desc, params = t.name, t.description, t.parameters
        else:
            # 检测到 dict 类型的工具定义 — 自动修复为 Tool 对象
            name = t.get("name", "unknown")
            desc = t.get("description", "")
            params = t.get("parameters", {})
            func = t.get("function")
            if name not in _warned_dict_tools:
                _warned_dict_tools.add(name)
                logger.info(
                    f"🔧 自动修复: TOOL_REGISTRY 中 {name} 为 dict 类型，"
                    f"已转换为 Tool 对象（原因为旧版 create_plugin 未使用 @register_tool）"
                )
            # 自愈：用 dict 内容构建 Tool 对象并替换
            if func is not None:
                TOOL_REGISTRY[key] = Tool(
                    name=name,
                    description=desc,
                    parameters=_ensure_schema(params),
                    function=func,
                    category=t.get("category", "misc"),
                    dangerous=t.get("dangerous", False),
                    requires_browser=t.get("requires_browser", False),
                    requires_db=t.get("requires_db", False),
                )
        result.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": _ensure_schema(params),
            }
        })
    return result


def _ensure_schema(params: dict) -> dict:
    """确保 parameters 是合法的 JSON Schema（防止 type: null 等 API 400 错误）"""
    if not isinstance(params, dict) or params is None:
        return {"type": "object", "properties": {}, "required": []}
    if not params.get("type"):
        return {"type": "object", "properties": params, "required": list(params.keys())}
    return params


def get_tool(name: str) -> Tool:
    """根据名称获取工具"""
    return TOOL_REGISTRY.get(name)


def execute_tool(name: str, args: dict) -> str:
    """执行工具并返回结果字符串"""
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return f"❌ 未知工具: {name}"

    # 兼容 dict 类型 — 现在理论上不会出现，但保留兜底
    if hasattr(tool, 'function'):
        func = tool.function
    else:
        func = tool.get("function")

    if func is None:
        return f"❌ 工具 {name} 无可执行函数"

    try:
        result = func(**args)
        return str(result) if result is not None else "✅ 完成"
    except Exception as e:
        logger.error(f"❌ 工具执行失败 {name}: {e}")
        return f"❌ 工具执行失败: {e}"
