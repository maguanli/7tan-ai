"""
代码搜索插件 — 提供 ripgrep 级别的项目级代码搜索能力
工具: grep_code, find_files, search_in_files
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import subprocess
import os

def _find_rg():
    """查找 ripgrep，找不到则回退到 Python 实现"""
    for rg in ["rg", "rg.exe"]:
        try:
            r = subprocess.run([rg, "--version"], capture_output=True, timeout=3)
            if r.returncode == 0:
                return rg
        except Exception:
            pass
    return None


@register_tool(
    name="grep_code",
    description="在项目目录中搜索代码内容（支持正则、文件类型过滤、上下文行数）。类似 VS Code 的全局搜索。",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "搜索关键词或正则表达式"},
            "path": {"type": "string", "description": "搜索根目录，默认当前工作目录", "default": "."},
            "file_types": {"type": "string", "description": "文件类型过滤，如 '*.py,*.js'", "default": ""},
            "context": {"type": "integer", "description": "显示匹配行上下文行数", "default": 2},
            "max_results": {"type": "integer", "description": "最大结果数", "default": 50},
        },
        "required": ["pattern"]
    },
    category="search"
)
def grep_code(pattern: str, path: str = ".", file_types: str = "",
              context: int = 2, max_results: int = 50) -> str:
    """在项目中 grep 搜索代码"""
    if not os.path.exists(path):
        return f"❌ 路径不存在: {path}"
    rg = _find_rg()
    if rg:
        cmd = [rg, "--line-number", "--color", "never",
               "--max-count", str(max_results)]
        if context > 0:
            cmd += ["-C", str(context)]
        if file_types:
            for ft in file_types.split(","):
                cmd += ["--glob", ft.strip()]
        cmd += ["-e", pattern, path]
    else:
        # 回退 Python 实现
        import re
        results = []
        try:
            compiled = re.compile(pattern)
        except re.error:
            return f"错误: 无效的正则表达式 '{pattern}'"

        # 收集目标文件：支持单文件路径（os.walk 对单文件返回空，需特殊处理）
        target_files = []
        if os.path.isfile(path):
            target_files = [path]
        else:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                           ("node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build")]
                for fname in files:
                    if file_types:
                        ext = os.path.splitext(fname)[1]
                        if f"*{ext}" not in file_types:
                            continue
                    target_files.append(os.path.join(root, fname))

        for fpath in target_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
                    lines = fp.readlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                if compiled.search(line):
                    if context > 0:
                        start = max(0, i - context - 1)
                        end = min(len(lines), i + context)
                        for j in range(start, end):
                            mark = ">" if j == i - 1 else " "
                            results.append(f"{fpath}:{j+1}:{mark} {lines[j].rstrip()}")
                    else:
                        results.append(f"{fpath}:{i}: {line.rstrip()}")
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break
        return "\n".join(results) if results else "未找到匹配结果"

    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=30)
        out = r.stdout.strip()
        return out if out else "未找到匹配结果"
    except subprocess.TimeoutExpired:
        return "搜索超时（30秒）"
    except Exception as e:
        return f"搜索失败: {e}"


@register_tool(
    name="find_files",
    description="按文件名模式查找文件，支持通配符和递归。用于快速定位项目中的文件。",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "文件名模式，如 '*.py' 或 'test_*'", "default": "*"},
            "path": {"type": "string", "description": "搜索根目录", "default": "."},
            "recursive": {"type": "boolean", "description": "是否递归搜索子目录", "default": True},
            "max_results": {"type": "integer", "description": "最大结果数", "default": 50},
        },
        "required": []
    },
    category="search"
)
def find_files(pattern: str = "*", path: str = ".", recursive: bool = True,
               max_results: int = 50) -> str:
    """按文件名查找"""
    import fnmatch
    # 路径存在检查，避免 WinError 3
    if not os.path.exists(path):
        return f"❌ 路径不存在: {path}\n💡 提示: 当前工作目录是 {os.getcwd()}，请确认路径是否正确。"
    # 单文件路径加固：os.walk 对单文件返回空、os.listdir 对单文件抛错，需特殊处理
    if os.path.isfile(path):
        if fnmatch.fnmatch(os.path.basename(path), pattern):
            size = os.path.getsize(path)
            return f"{path} ({size:,} bytes)"
        return f"未找到匹配 '{pattern}' 的文件"
    results = []
    walker = os.walk(path) if recursive else [(path, [], os.listdir(path))]
    for root, dirs, files in walker:
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build")]
        for fname in files:
            if fnmatch.fnmatch(fname, pattern):
                fpath = os.path.join(root, fname)
                size = os.path.getsize(fpath)
                results.append(f"{fpath} ({size:,} bytes)")
                if len(results) >= max_results:
                    break
        if len(results) >= max_results:
            break
    return "\n".join(results) if results else f"未找到匹配 '{pattern}' 的文件"


@register_tool(
    name="search_in_files",
    description="在指定文件列表中搜索内容，适合在之前 find_files 的结果中进一步搜索。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索内容"},
            "files": {"type": "string", "description": "文件路径列表（换行分隔）"},
            "case_sensitive": {"type": "boolean", "description": "是否区分大小写", "default": False},
        },
        "required": ["query", "files"]
    },
    category="search"
)
def search_in_files(query: str, files: str, case_sensitive: bool = False) -> str:
    """在指定文件列表中搜索"""
    file_list = [f.split(" ")[0].strip() for f in files.split("\n") if f.strip()]
    if not file_list:
        return "未提供有效的文件列表"
    results = []
    q = query if case_sensitive else query.lower()
    for fpath in file_list:
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
                for i, line in enumerate(fp, 1):
                    l = line if case_sensitive else line.lower()
                    if q in l:
                        results.append(f"{fpath}:{i}: {line.rstrip()}")
                        if len(results) >= 50:
                            break
        except Exception:
            pass
        if len(results) >= 50:
            break
    return "\n".join(results) if results else f"未找到包含 '{query}' 的行"
