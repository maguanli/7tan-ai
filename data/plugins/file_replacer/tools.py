
"""文件内容替换工具"""
import subprocess
import sys
from pathlib import Path

from src.tools.registry import register_tool


@register_tool(
    name="file_replace",
    description="对文本文件执行字符串替换。支持多个替换对。",
    parameters={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "要修改的文件路径"},
            "replacements": {"type": "string", "description": "替换对，JSON 格式: {\"旧字符串\": \"新字符串\", ...}"},
        },
        "required": ["filepath", "replacements"]
    },
    category="file_ops",
    dangerous=False,
)
def file_replace(filepath: str, replacements: str) -> str:
    """在文件中执行字符串替换"""
    import json
    path = Path(filepath)
    if not path.exists():
        return f"❌ 文件不存在: {filepath}"
    
    try:
        reps = json.loads(replacements)
        content = path.read_text(encoding="utf-8")
        original = content
        for old, new in reps.items():
            count = content.count(old)
            content = content.replace(old, new)
        
        if content == original:
            return f"⚠️ 未找到任何匹配的字符串，文件未修改"
        
        path.write_text(content, encoding="utf-8")
        
        changes = []
        for old, new in reps.items():
            cnt = original.count(old)
            if cnt > 0:
                changes.append(f"  '{old}' → '{new}' ({cnt} 处)")
        
        return f"✅ 已修改: {filepath}\n" + "\n".join(changes)
    except Exception as e:
        return f"❌ 替换失败: {e}"
