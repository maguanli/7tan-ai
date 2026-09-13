"""
工具注册中心 — 统一管理和注册 AI 可调用的工具

2026-09-01 起：7Tan AI 已开源，移除 Pro 门控，self_modify 类工具对所有用户开放。
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
    pro_only: bool = False       # 已废弃：开源后无门控，保留字段仅为兼容


# 全局注册表
TOOL_REGISTRY: dict[str, Tool] = {}

# 已警告过的 dict 类型工具名（避免重复告警）
_warned_dict_tools: set = set()

# Pro 门控缓存：减少每次执行都验签的开销
_gate_cache: dict = {"checked": False, "is_pro": False, "pro_license": ""}


def _check_pro_status() -> bool:
    """检查当前用户等级（门控已废弃）。

    2026-09-01 起：7Tan AI 已开源，移除 Pro 门控。
    本函数恒返回 True，保留仅为兼容旧调用点（get_all_tools / execute_tool / UI）。
    """
    return True


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
        logger.debug(f"🔧 注册工具: {tool.name} ({tool.category})")
        return target
    return decorator


def get_all_tools(include_pro_only: bool = None) -> list[dict]:
    """返回 OpenAI 兼容的 tools 数组。
    
    Args:
        include_pro_only: 已废弃参数（开源后无门控）。
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


def _feed_tan_model(tool_name: str, args: dict, success: bool) -> None:
    """把工具真实执行结果回写给 7Tan 模型记忆库（方案B：主系统数据自动成为训练数据）。

    场景 = "tool:<工具名>"，动作 = 参数摘要（只存键名 + 短值，避免大内容进记忆）。
    全部异常静默，绝不影响主流程（学习是副产物，不是依赖）。

    ── 阶段六修复5：工具成败喂入器官总线（真实失败样本通道）──
    修复前：limitations 只能从对话模式产生（回复即成功，永远成功）→ 自我模型的
    局限条目在自然运行中无法从真实失败中长出来。
    现在：① tool_result 事件（带 ok 标志）上总线（origin=external，真实生产工具流
    对 ORG-F 可见）；② goal 思想碎片（goal_tag=tool:<名>, success=成败）压入工作
    记忆 → CONSOLIDATE 巩固 → SELFMODEL 自然归纳：常用工具成功 → capability，
    反复失败的工具 → limitations（测试3/4 的失败侧数据源自此闭环）。
    """
    try:
        from src.agent.bionic_organs import emit_event, wm_push_thought
        emit_event("tool_result", {
            "tool": tool_name,
            "ok": bool(success),
            "summary": "执行成功" if success else "执行失败",
            "args_keys": list((args or {}).keys())[:8],
        }, source="TOOL_REGISTRY", origin="external")
        # 失败比成功更显眼（负性偏差）：focus/valence 拉高，保证幼年门槛下也能巩固
        _focus = 0.5 if success else 0.75
        _val = 0.3 if success else -0.5
        wm_push_thought(
            f"goal:tool:{tool_name} 已执行(结果={'成功' if success else '失败'})",
            focus=_focus,
            valence=_val,
            origin="internal",
            goal_tag=f"tool:{tool_name}",
            success=bool(success),
        )
    except Exception:
        pass
    try:
        from src.agent.world_model import get_tan_model
        model = get_tan_model()
        parts = []
        for k, v in (args or {}).items():
            s = "" if v is None else str(v)
            parts.append(f"{k}={s[:40]}" + ("…" if len(s) > 40 else ""))
        action = (",".join(parts))[:120] or "run"
        scene = f"tool:{tool_name}"
        model.memory.add_trace(
            scene=scene,
            action=action,
            finished=bool(success),
            changed=False,
            reduced=False,
            gained=True,  # 每次真实执行都是经验
        )
        # 只有模型此前对该场景（scene=动作摘要的任一预测）有过预测 → 才触发完整闭环
        # 否则只入库不闭环，避免 PE 历史被无对照的满误差污染
        try:
            preds = getattr(model, "_last_predictions", {}) or {}
            has_pred = any(str(k[0]) == scene for k in preds)
            if has_pred and hasattr(model, "_selflearn_after_record"):
                model._last_record = model.memory.traces[-1]
                extra = model._selflearn_after_record()
                if extra:
                    logger.debug(f"🧠 7Tan模型闭环（工具 {tool_name}）: {extra.splitlines()[0][:60]}")
        except Exception:
            pass
    except Exception:
        pass


def _result_is_error(result) -> bool:
    """业务失败检测：工具返回以 ❌ 开头的错误字符串（项目内失败约定），
    或返回 None（视为完成但无内容）。"""
    return isinstance(result, str) and result.startswith("❌")


def execute_tool(name: str, args: dict) -> str:
    """执行工具并返回结果字符串。
    """
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        # 阶段六修复5：调用了不存在的工具 = 真实失败经历（LLM 幻觉工具名）
        # 喂入器官总线，让自我模型能从这类失败中长出 limitations
        _feed_tan_model(name, args or {}, False)
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
        _feed_tan_model(name, args, not _result_is_error(result))
        return str(result) if result is not None else "✅ 完成"
    except Exception as e:
        _feed_tan_model(name, args, False)
        logger.error(f"❌ 工具执行失败 {name}: {e}")
        return f"❌ 工具执行失败: {e}"
