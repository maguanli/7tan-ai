"""
记忆增强插件 — 持久化知识存储与检索（数据库版）
让 AI 能够记住重要信息、积累经验、跨会话保持知识
所有数据存储到 SQLite 数据库 games.db，不再使用 JSON 文件
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


def _get_db_funcs():
    """延迟导入数据库函数，避免循环依赖"""
    from src.database.db import (
        upsert_memory, get_all_memories, get_memory_summary, delete_memory
    )
    return upsert_memory, get_all_memories, get_memory_summary, delete_memory


@register_tool(
    name="memory_store",
    description="存储一条知识/记忆到持久化存储中。用于记住重要信息，重启后依然存在。分为 games(游戏知识)/skills(技能经验)/config(配置)/general(通用)。",
    parameters={
        "type": "object",
        "properties": {
            "section": {"type": "string", "description": "记忆分类"},
            "key": {"type": "string", "description": "记忆键名"},
            "content": {"type": "string", "description": "记忆内容"},
            "importance": {"type": "string", "description": "重要程度：high/medium/low", "default": "medium"},
        },
        "required": ["section", "key", "content"],
    },
    category="memory",
)
def memory_store(section: str, key: str, content: str, importance: str = "medium") -> str:
    upsert_memory, _, _, _ = _get_db_funcs()
    try:
        result = upsert_memory(section, key, content, importance)
        action = "更新" if result["action"] == "updated" else "存储"
        return f"✅ 已{action}记忆 [{section}/{key}] (重要性: {importance})"
    except Exception as e:
        return f"❌ 存储失败: {e}"


@register_tool(
    name="memory_recall",
    description="检索记忆。按分类和关键词搜索已存储的知识。用于回忆之前学到的经验。",
    parameters={
        "type": "object",
        "properties": {
            "section": {"type": "string", "description": "记忆分类，留空=全部"},
            "keyword": {"type": "string", "description": "搜索关键词", "default": ""},
            "limit": {"type": "integer", "description": "最多返回条数", "default": 10},
        },
        "required": [],
    },
    category="memory",
)
def memory_recall(section: str = "", keyword: str = "", limit: int = 10) -> str:
    _, get_all_memories, _, _ = _get_db_funcs()
    try:
        results = get_all_memories(
            section=section if section else None,
            keyword=keyword if keyword else None,
            limit=limit,
        )
        if not results:
            return f"🔍 未找到匹配的记忆（分类={section or '全部'}, 关键词={keyword or '无'}）"

        importance_order = {"high": 0, "medium": 1, "low": 2}
        results.sort(key=lambda x: importance_order.get(x.get("importance", "low"), 3))

        output = [f"🧠 记忆检索结果 ({len(results)} 条):\n"]
        for r in results:
            output.append(f"  [{r['section']}/{r['key']}] ⭐{r.get('importance', '?')}")
            output.append(f"    {r['content'][:200]}")
            output.append("")
        return "\n".join(output)
    except Exception as e:
        return f"❌ 检索失败: {e}"


@register_tool(
    name="memory_summary",
    description="查看记忆存储概览：各分区条目数、最近更新等。",
    parameters={
        "type": "object", "properties": {}, "required": [],
    },
    category="memory",
)
def memory_summary() -> str:
    _, _, get_memory_summary, _ = _get_db_funcs()
    try:
        sections = get_memory_summary()
        if not sections:
            return "🧠 记忆存储为空"

        output = ["🧠 记忆存储概览\n"]
        total = 0
        for s in sections:
            total += s["total"]
            output.append(
                f"  📁 {s['section']}: {s['total']} 条 "
                f"(重要:{s['high_count']}) | 更新:{s['last_updated']}"
            )
        output.append(f"\n  📊 总计: {total} 条记忆")
        return "\n".join(output)
    except Exception as e:
        return f"❌ 获取概览失败: {e}"


@register_tool(
    name="memory_forget",
    description="删除一条记忆。",
    parameters={
        "type": "object",
        "properties": {
            "section": {"type": "string", "description": "记忆分类"},
            "key": {"type": "string", "description": "要删除的记忆键名"},
        },
        "required": ["section", "key"],
    },
    category="memory",
)
def memory_forget(section: str, key: str) -> str:
    _, _, _, delete_memory = _get_db_funcs()
    try:
        if delete_memory(section, key):
            return f"🗑️ 已删除记忆 [{section}/{key}]"
        return f"⚠️ 未找到记忆 [{section}/{key}]"
    except Exception as e:
        return f"❌ 删除失败: {e}"
