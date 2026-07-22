"""
代码片段管理器 — 保存、搜索、复用代码片段
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import json as _json
import os

SNIPPETS_FILE = Path(__file__).parent / "snippets.json"


def _load() -> dict:
    if SNIPPETS_FILE.exists():
        try:
            with open(SNIPPETS_FILE, "r", encoding="utf-8") as f:
                return _json.load(f)
        except Exception:
            pass
    return {"snippets": {}}


def _save(data: dict):
    with open(SNIPPETS_FILE, "w", encoding="utf-8") as f:
        _json.dump(data, f, ensure_ascii=False, indent=2)


@register_tool(
    name="save_snippet",
    description="保存代码片段到跨项目代码库。支持标签分类和语言标记。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "片段名称"},
            "code": {"type": "string", "description": "代码内容"},
            "language": {"type": "string", "description": "语言: python/js/ts/go/rust/sql/html/bash 等", "default": "python"},
            "tags": {"type": "string", "description": "标签（逗号分隔），如 'auth,flask,middleware'", "default": ""},
            "description": {"type": "string", "description": "简短描述", "default": ""},
        },
        "required": ["name", "code"]
    },
    category="snippet"
)
def save_snippet(name: str, code: str, language: str = "python",
                 tags: str = "", description: str = "") -> str:
    """保存代码片段"""
    from datetime import datetime
    data = _load()
    data["snippets"][name] = {
        "code": code,
        "language": language,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "description": description,
        "saved_at": datetime.now().isoformat(),
    }
    _save(data)
    return f"✅ 片段已保存: {name} ({language}, {len(code)} 字符)"


@register_tool(
    name="search_snippets",
    description="搜索已保存的代码片段。按名称、标签、语言或关键词搜索。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词（匹配名称、标签、语言）", "default": ""},
            "language": {"type": "string", "description": "按语言筛选", "default": ""},
            "tag": {"type": "string", "description": "按标签筛选", "default": ""},
        },
        "required": []
    },
    category="snippet"
)
def search_snippets(query: str = "", language: str = "",
                    tag: str = "") -> str:
    """搜索片段"""
    data = _load()
    snippets = data.get("snippets", {})
    if not snippets:
        return "📭 片段库为空。使用 save_snippet 添加。\n\n示例片段: Python Flask API、Node.js Express路由、SQL 查询模板等。"

    q = query.lower()
    results = []
    for name, info in snippets.items():
        lang = info.get("language", "")
        tags = info.get("tags", [])
        desc = info.get("description", "")
        if language and language != lang:
            continue
        if tag and tag not in tags:
            continue
        if q:
            if q not in name.lower() and q not in " ".join(tags).lower() and q not in desc.lower() and q not in lang.lower():
                continue
        results.append(f"  📌 {name} [{lang}] {' '.join('#'+t for t in tags)}\n     {desc}")

    if not results:
        return f"未找到匹配片段 (query='{query}', lang='{language}', tag='{tag}')"
    return f"📦 代码片段 ({len(results)} 个):\n\n" + "\n\n".join(results)


@register_tool(
    name="get_snippet",
    description="获取已保存代码片段的完整内容。用于复制或引用已有代码。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "片段名称"},
        },
        "required": ["name"]
    },
    category="snippet"
)
def get_snippet(name: str) -> str:
    """获取片段内容"""
    data = _load()
    info = data.get("snippets", {}).get(name)
    if not info:
        return f"片段 '{name}' 不存在。使用 search_snippets 查看所有片段。"

    lang = info.get("language", "")
    code = info.get("code", "")
    tags = info.get("tags", [])

    return (f"📌 {name} [{lang}] {' '.join('#'+t for t in tags)}\n"
            f"```{lang}\n{code}\n```")


@register_tool(
    name="list_snippets",
    description="列出所有已保存的代码片段，按语言分组。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="snippet"
)
def list_snippets() -> str:
    """列出所有片段"""
    data = _load()
    snippets = data.get("snippets", {})
    if not snippets:
        return "📭 片段库为空"

    from collections import defaultdict
    by_lang = defaultdict(list)
    for name, info in snippets.items():
        by_lang[info.get("language", "other")].append(name)

    lines = [f"📦 代码片段库 ({len(snippets)} 个):\n"]
    for lang in sorted(by_lang):
        lines.append(f"  [{lang}]:")
        for name in sorted(by_lang[lang]):
            info = snippets[name]
            lines.append(f"    • {name} — {info.get('description', '无描述')}")
    return "\n".join(lines)
