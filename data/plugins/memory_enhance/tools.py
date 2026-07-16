"""
记忆增强插件 — 持久化知识存储与检索
让 AI 能够记住重要信息、积累经验、跨会话保持知识
"""
import sys, json, os, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# 往上查找 build.bat，定位真正的源码根目录（避免 dist 被清空）
_real_root = ROOT
for _ in range(6):
    if (_real_root / "build.bat").exists():
        break
    _real_root = _real_root.parent

MEMORY_DIR = _real_root / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _read_memory(section: str) -> dict:
    path = MEMORY_DIR / f"{section}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except:
            return {"entries": [], "updated": str(datetime.now())}
    return {"entries": [], "updated": str(datetime.now()), "created": str(datetime.now())}


def _write_memory(section: str, data: dict):
    path = MEMORY_DIR / f"{section}.json"
    data["updated"] = str(datetime.now())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    mem = _read_memory(section)
    existing = [e for e in mem["entries"] if e.get("key") == key]
    if existing:
        existing[0]["content"] = content
        existing[0]["importance"] = importance
        existing[0]["updated"] = str(datetime.now())
        _write_memory(section, mem)
        return f"🔄 已更新记忆 [{section}/{key}]"
    
    mem["entries"].append({
        "key": key, "content": content, "importance": importance,
        "created": str(datetime.now()), "updated": str(datetime.now()),
    })
    if len(mem["entries"]) > 500:
        mem["entries"] = sorted(mem["entries"], key=lambda x: x.get("importance","low")!="high")
        mem["entries"] = mem["entries"][:500]
    
    _write_memory(section, mem)
    return f"✅ 已存储记忆 [{section}/{key}] (重要性: {importance})"


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
    results = []
    sections = [section] if section else [p.stem for p in MEMORY_DIR.glob("*.json")]
    
    for sec in sections:
        mem = _read_memory(sec)
        for entry in mem.get("entries", []):
            if keyword:
                kw = keyword.lower()
                if kw not in entry.get("key","").lower() and kw not in entry.get("content","").lower():
                    continue
            results.append({"section": sec, **entry})
    
    if not results:
        return f"🔍 未找到匹配的记忆（分类={section or '全部'}, 关键词={keyword or '无'}）"
    
    importance_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: importance_order.get(x.get("importance","low"), 3))
    results = results[:limit]
    
    output = [f"🧠 记忆检索结果 ({len(results)} 条):\n"]
    for r in results:
        output.append(f"  [{r['section']}/{r['key']}] ⭐{r.get('importance','?')}")
        output.append(f"    {r['content'][:200]}")
        output.append("")
    return "\n".join(output)


@register_tool(
    name="memory_summary",
    description="查看记忆存储概览：各分区条目数、最近更新等。",
    parameters={
        "type": "object", "properties": {}, "required": [],
    },
    category="memory",
)
def memory_summary() -> str:
    output = ["🧠 记忆存储概览\n"]
    total = 0
    for path in sorted(MEMORY_DIR.glob("*.json")):
        mem = _read_memory(path.stem)
        count = len(mem.get("entries", []))
        total += count
        high = sum(1 for e in mem.get("entries", []) if e.get("importance") == "high")
        updated = mem.get("updated", "?")
        output.append(f"  📁 {path.stem}: {count} 条 (重要:{high}) | 更新:{updated[:19]}")
    output.append(f"\n  📊 总计: {total} 条记忆")
    return "\n".join(output)


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
    mem = _read_memory(section)
    before = len(mem["entries"])
    mem["entries"] = [e for e in mem["entries"] if e.get("key") != key]
    after = len(mem["entries"])
    if before == after:
        return f"⚠️ 未找到记忆 [{section}/{key}]"
    _write_memory(section, mem)
    return f"🗑️ 已删除记忆 [{section}/{key}] ({before}→{after})"
