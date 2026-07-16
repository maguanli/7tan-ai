
"""文件内容批量替换工具"""
import json
from pathlib import Path


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
    
    try:
        reps = json.loads(replacements)
        content = path.read_text(encoding="utf-8")
        original = content
        for old, new in reps.items():
            content = content.replace(old, new)
        
        if content == original:
            return f"⚠️ 未找到任何匹配的字符串，文件未修改"
        
        path.write_text(content, encoding="utf-8")
        
        changes = []
        for old, new in reps.items():
            cnt = original.count(old)
            if cnt > 0:
                changes.append(f"  '{old[:50]}' → '{new[:50]}' ({cnt} 处)")
        
        return f"✅ 已修改: {filepath}\n" + "\n".join(changes)
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析失败: {e}"
    except UnicodeDecodeError:
        return f"❌ 文件不是文本格式或编码不支持: {filepath}"
    except Exception as e:
        return f"❌ 替换失败: {e}"


def register(registry_func):
    """注册文件替换工具到全局注册表"""
    registry_func(
        name="file_replace",
        description="对文本文件执行批量字符串替换。支持多个替换对一次性执行，JSON 格式配置。",
        parameters={
            "filepath": {"type": "string", "description": "要修改的文件完整路径"},
            "replacements": {"type": "string", "description": "替换对，JSON 格式: {\"旧字符串\": \"新字符串\", ...}"}
        },
        category="file_ops"
    )(file_replace)
