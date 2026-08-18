"""
工具注册中心 — 统一管理和注册 AI 可调用的工具

Pro 等级门控：self_modify 类工具仅完整版（pro）用户可调用。
基础版（free）用户调用时会被拦截并返回提示。
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
    pro_only: bool = False       # 仅完整版可用（self_modify 类自动设为 True）


# 全局注册表
TOOL_REGISTRY: dict[str, Tool] = {}

# 已警告过的 dict 类型工具名（避免重复告警）
_warned_dict_tools: set = set()

# Pro 门控缓存：减少每次执行都验签的开销
_gate_cache: dict = {"checked": False, "is_pro": False, "pro_license": ""}


def _check_pro_status() -> bool:
    """检查当前用户是否为完整版（带缓存）。"""
    global _gate_cache

    # 每次重新检查，最多缓存 60 秒
    import time
    now = time.time()
    if _gate_cache.get("checked") and (now - _gate_cache.get("ts", 0) < 60):
        return _gate_cache["is_pro"]

    try:
        from ..security.token_store import load_token
        from ..security.license_verify import verify_license, LicenseError

        token_data = load_token()
        pro_license = (token_data.get("pro_license") or "") if token_data else ""

        if pro_license:
            try:
                result = verify_license(pro_license)
                is_pro = result.get("level") == "pro"
                _gate_cache = {"checked": True, "is_pro": is_pro, "pro_license": pro_license, "ts": now}
                return is_pro
            except LicenseError:
                pass

        # ⚠️ 安全修复：不再信任 token 中的本地 level 字段（可被本地文件篡改伪造 Pro）
        # 仅接受 license 验签结果；验签失败一律按非 Pro 处理

        _gate_cache = {"checked": True, "is_pro": False, "pro_license": "", "ts": now}
        return False
    except Exception as e:
        logger.debug(f"[ProGate] 状态检查异常: {e}")
        _gate_cache = {"checked": True, "is_pro": False, "pro_license": "", "ts": now}
        return False


def invalidate_pro_cache() -> None:
    """清除 Pro 门控缓存（刷新 Token 后调用）。"""
    global _gate_cache
    _gate_cache = {"checked": False, "is_pro": False, "pro_license": ""}


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
                pro_only=(category == "self_modify"),
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
                pro_only=(category == "self_modify"),
            )
        TOOL_REGISTRY[tool.name] = tool
        logger.debug(f"🔧 注册工具: {tool.name} ({tool.category}) {'🔒PRO' if tool.pro_only else ''}")
        return target
    return decorator


def get_all_tools(include_pro_only: bool = None) -> list[dict]:
    """返回 OpenAI 兼容的 tools 数组。
    
    Args:
        include_pro_only: 是否包含完整版专属工具。
            None (默认): 自动检测当前用户等级
            True: 始终包含
            False: 始终排除
    """
    # 自动检测：free 用户不暴露 self_modify 工具给 AI
    if include_pro_only is None:
        include_pro_only = _check_pro_status()
    result = []
    for key, t in list(TOOL_REGISTRY.items()):
        # 兼容插件可能注册 dict 而不是 Tool（旧版本遗留问题）
        if hasattr(t, 'name'):
            name, desc, params, pro_only = t.name, t.description, t.parameters, getattr(t, 'pro_only', False)
        else:
            # 检测到 dict 类型的工具定义 — 自动修复为 Tool 对象
            name = t.get("name", "unknown")
            desc = t.get("description", "")
            params = t.get("parameters", {})
            func = t.get("function")
            cat = t.get("category", "misc")
            pro_only = (cat == "self_modify")
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
                    category=cat,
                    dangerous=t.get("dangerous", False),
                    requires_browser=t.get("requires_browser", False),
                    requires_db=t.get("requires_db", False),
                    pro_only=pro_only,
                )

        # Pro 门控：free 用户不暴露 self_modify 工具给 AI
        if pro_only and not include_pro_only:
            continue

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
    """执行工具并返回结果字符串。
    
    Pro 门控：self_modify 类工具仅完整版用户可调用。
    """
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return f"❌ 未知工具: {name}"

    # ── Pro 等级门控 ───────────────────────────────────────
    # 通过 Tool.pro_only 属性判断（比 category 判断更可靠）
    is_pro_only = getattr(tool, 'pro_only', False) or getattr(tool, 'category', '') == 'self_modify'

    if is_pro_only and not _check_pro_status():
        logger.warning(f"🔒 [ProGate] 拦截 free 用户调用完整版工具: {name}")
        return (
            f"🔒 权限不足：`{name}` 是完整版专属功能。\n\n"
            "基础版（free）用户无法使用自修改类工具（self_modify_config / sandbox_execute / "
            "self_rebuild / self_update_prompt 等）。\n\n"
            "💡 **升级到完整版**即可解锁：https://www.7tan.com/pro.php\n"
            "完整版权益：自我修改、自定义提示词、自动重建、优先支持。"
        )

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
