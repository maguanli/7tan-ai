"""
文件操作工具 — 本地文件读写删查
"""
import json as _json
import shutil
from pathlib import Path

from .registry import register_tool
from ..utils.helpers import ensure_dir, human_readable_size


@register_tool(
    name="list_files",
    description="列出目录下的所有文件，支持筛选扩展名",
    parameters={
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "目录路径"},
            "pattern": {"type": "string", "description": "文件扩展名筛选，如 .zip .rar", "default": "*"},
        },
        "required": ["directory"]
    },
    category="file",
)
def list_files(directory: str, pattern: str = "*") -> str:
    """列出文件"""
    p = Path(directory)
    if not p.exists():
        return f"❌ 目录不存在: {directory}"

    # 规范化 pattern — 去除可能的前缀匹配符号
    clean_pattern = pattern.strip()
    if clean_pattern.startswith("**/"):
        # 已经是递归模式
        clean_pattern = clean_pattern[3:] or "*"
        files = sorted(p.rglob(clean_pattern))
    elif clean_pattern == "**":
        files = sorted(p.rglob("*"))
    elif "**" in clean_pattern:
        # 去除混在中间的 **
        clean_pattern = clean_pattern.replace("**", "")
        files = sorted(p.rglob(clean_pattern))
    elif clean_pattern != "*":
        files = sorted(p.glob(clean_pattern))
        if not files:
            files = sorted(p.rglob(clean_pattern))
    else:
        files = sorted(p.iterdir())

    if not files:
        return f"📂 目录为空: {directory}"

    lines = [f"📂 {directory} ({len(files)} 个文件/目录):\n"]
    for f in files[:50]:
        prefix = "📁" if f.is_dir() else "📄"
        size = human_readable_size(f.stat().st_size) if f.is_file() else "-"
        lines.append(f"  {prefix} {f.name} ({size})")

    if len(files) > 50:
        lines.append(f"  ... 还有 {len(files) - 50} 个")

    return "\n".join(lines)


@register_tool(
    name="read_file_content",
    description="读取文件内容（支持文本文件和 JSON）。可通过 offset 指定起始行，max_lines 限制行数。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "encoding": {"type": "string", "description": "编码", "default": "utf-8"},
            "max_lines": {"type": "integer", "description": "最大读取行数", "default": 200},
            "offset": {"type": "integer", "description": "从第几行开始读取（0=第一行）", "default": 0},
        },
        "required": ["path"]
    },
    category="file",
)
def read_file_content(path: str, encoding: str = "utf-8", max_lines: int = 200, offset: int = 0) -> str:
    """读取文件内容"""
    p = Path(path)
    if not p.exists():
        return f"❌ 文件不存在: {path}"

    try:
        if p.suffix == ".json":
            data = _json.loads(p.read_text(encoding=encoding))
            return f"📄 {p.name} (JSON):\n" + _json.dumps(data, ensure_ascii=False, indent=2)[:5000]
        else:
            all_lines = p.read_text(encoding=encoding).split("\n")
            total = len(all_lines)
            # 应用 offset
            if offset > 0:
                all_lines = all_lines[offset:]
            if len(all_lines) > max_lines:
                content = "\n".join(all_lines[:max_lines])
                return f"📄 {p.name} (共 {total} 行，offset={offset}，显示前 {max_lines} 行):\n```\n{content}\n```"
            return f"📄 {p.name}:\n```\n" + "\n".join(all_lines) + "\n```"
    except Exception as e:
        return f"❌ 读取失败: {e}"


@register_tool(
    name="write_file",
    description="写入文本文件到本地",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "要写入的内容"},
            "encoding": {"type": "string", "description": "编码", "default": "utf-8"},
        },
        "required": ["path", "content"]
    },
    category="file",
    dangerous=True,
)
def write_file_content(path: str, content: str, encoding: str = "utf-8") -> str:
    """写入文件"""
    p = Path(path)
    ensure_dir(str(p.parent))
    try:
        p.write_text(content, encoding=encoding)
        return f"✅ 已写入: {path} ({len(content)} 字符)"
    except Exception as e:
        return f"❌ 写入失败: {e}"


@register_tool(
    name="delete_file",
    description="删除本地文件或目录",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要删除的文件/目录路径"},
        },
        "required": ["path"]
    },
    category="file",
    dangerous=True,
)
def delete_file(path: str) -> str:
    """删除文件或目录"""
    p = Path(path)
    if not p.exists():
        return f"❌ 不存在: {path}"

    try:
        if p.is_dir():
            shutil.rmtree(p)
            return f"🗑️ 已删除目录: {path}"
        else:
            p.unlink()
            return f"🗑️ 已删除: {path}"
    except Exception as e:
        return f"❌ 删除失败: {e}"
