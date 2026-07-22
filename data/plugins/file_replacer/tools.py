"""
文件内容批量替换工具
"""
import json
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="file_replace",
    description="对文本文件执行批量字符串替换。支持多个替换对一次性执行，JSON 格式配置。",
    parameters={
        "filepath": {"type": "string", "description": "要修改的文件完整路径"},
        "replacements": {"type": "string", "description": "替换对，JSON 格式: {\"旧字符串\": \"新字符串\", ...}"}
    },
    category="file_ops"
)
def file_replace(filepath: str, replacements: str) -> str:
    """在文本文件中执行批量字符串替换。支持多个替换对一次性执行。
    
    参数:
        filepath: 要修改的文件完整路径
        replacements: 替换对，JSON 格式字符串。例如: {"旧字符串1": "新字符串1", "旧字符串2": "新字符串2"}
    
    示例:
        file_replace("D:\\test.txt", '{"hello": "你好", "world": "世界"}')
    """
    path = Path(filepath)
    if not path.exists():
        return f"❌ 文件不存在: {filepath}"
    
    # 解析替换对：JSON → Python dict 回退 → 直接使用 dict
    try:
        if isinstance(replacements, dict):
            reps = replacements
        else:
            try:
                reps = json.loads(replacements)
            except (json.JSONDecodeError, TypeError) as je:
                # 回退：尝试 Python dict 字面量（ast.literal_eval）
                reps = ast.literal_eval(replacements)
                if not isinstance(reps, dict):
                    return f"❌ 替换对解析后不是 dict 类型，而是 {type(reps).__name__}"
    except (ValueError, SyntaxError) as e:
        # 两种解析都失败，给出详细错误
        preview = str(replacements)[:200]
        return f"❌ 替换对格式错误: {e}\n原始内容预览: {preview}...\n💡 请确保是有效的 JSON 或 Python dict 格式"
    
    if not reps:
        return "❌ 替换对为空，无需修改"
    
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"❌ 文件不是文本格式或编码不支持: {filepath}"
    except Exception as e:
        return f"❌ 读取文件失败: {e}"
    
    original = content
    for old, new in reps.items():
        content = content.replace(old, new)
    
    if content == original:
        # 列出尝试过的替换，帮助排查
        tried = [f"  '{k[:40]}'" for k in reps.keys()]
        return f"⚠️ 未找到任何匹配的字符串，文件未修改。尝试了:\n" + "\n".join(tried)
    
    try:
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"❌ 写入文件失败: {e}"
    
    changes = []
    for old, new in reps.items():
        cnt = original.count(old)
        if cnt > 0:
            changes.append(f"  '{old[:50]}' → '{new[:50]}' ({cnt} 处)")
    
    return f"✅ 已修改: {filepath}\n" + "\n".join(changes)
