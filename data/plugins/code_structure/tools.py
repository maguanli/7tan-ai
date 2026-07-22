"""
代码结构分析插件 — Python/JS AST 解析，函数/类列表，引用查找，导入分析
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import ast as _ast
import os


@register_tool(
    name="list_functions",
    description="列出 Python 文件中的所有函数和类定义，包括装饰器、参数和文档字符串。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
        },
        "required": ["file_path"]
    },
    category="code"
)
def list_functions(file_path: str) -> str:
    """解析 Python 文件结构"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = _ast.parse(source, filename=file_path)
    except SyntaxError as e:
        return f"语法错误: {e}"
    except Exception as e:
        return f"解析失败: {e}"

    results = [f"文件: {file_path} ({len(source.splitlines())} 行)"]
    for node in _ast.walk(tree):
        if isinstance(node, _ast.FunctionDef):
            decos = [f"@{_ast.unparse(d)}" for d in node.decorator_list] if node.decorator_list else []
            args = _ast.unparse(node.args)
            doc = _ast.get_docstring(node)
            prefix = "  ├─ 装饰器: " + ", ".join(decos) if decos else ""
            results.append(f"  📍 函数 def {node.name}({args})  (行 {node.lineno})")
            if prefix:
                results.append(prefix)
            if doc:
                results.append(f"  │  Doc: {doc[:80]}...")
        elif isinstance(node, _ast.AsyncFunctionDef):
            decos = [f"@{_ast.unparse(d)}" for d in node.decorator_list] if node.decorator_list else []
            results.append(f"  📍 异步函数 async def {node.name}  (行 {node.lineno})")
        elif isinstance(node, _ast.ClassDef):
            bases = [_ast.unparse(b) for b in node.bases] if node.bases else []
            decos = [f"@{_ast.unparse(d)}" for d in node.decorator_list] if node.decorator_list else []
            methods = sum(1 for m in node.body if isinstance(m, (_ast.FunctionDef, _ast.AsyncFunctionDef)))
            results.append(f"  📦 类 class {node.name}({', '.join(bases)})  (行 {node.lineno}, {methods} 方法)")
            if decos:
                results.append(f"  ├─ 装饰器: {', '.join(decos)}")
    return "\n".join(results)


@register_tool(
    name="analyze_imports",
    description="分析 Python 文件的导入依赖：列出所有 import 语句，区分标准库/第三方/内部导入。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
        },
        "required": ["file_path"]
    },
    category="code"
)
def analyze_imports(file_path: str) -> str:
    """分析导入依赖"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = _ast.parse(source, filename=file_path)
    except Exception as e:
        return f"解析失败: {e}"

    stdlib = set()
    third_party = set()
    internal = set()
    stdlib_names = {
        "os", "sys", "re", "json", "time", "datetime", "pathlib", "collections",
        "typing", "abc", "itertools", "functools", "subprocess", "threading",
        "hashlib", "base64", "math", "random", "io", "csv", "logging", "argparse",
        "ast", "inspect", "traceback", "unittest", "textwrap", "shutil", "tempfile",
        "glob", "fnmatch", "pickle", "sqlite3", "urllib", "http", "email", "xml",
        "html", "socket", "ssl", "asyncio", "concurrent", "multiprocessing",
        "dataclasses", "enum", "copy", "weakref", "pprint", "statistics",
    }

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in stdlib_names:
                    stdlib.add(alias.name)
                elif top.startswith("src") or top.startswith("."):
                    internal.add(alias.name)
                else:
                    third_party.add(alias.name)
        elif isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            top = mod.split(".")[0]
            if top in stdlib_names or not top:
                stdlib.add(mod)
            elif top.startswith("src") or node.level > 0:
                internal.add(mod)
            else:
                third_party.add(mod)

    results = [f"📊 {file_path} 导入分析:"]
    if stdlib:
        results.append(f"\n🏛️ 标准库 ({len(stdlib)}): {', '.join(sorted(stdlib))}")
    if third_party:
        results.append(f"\n📦 第三方库 ({len(third_party)}): {', '.join(sorted(third_party))}")
    if internal:
        results.append(f"\n🔗 内部导入 ({len(internal)}): {', '.join(sorted(internal))}")
    if not any([stdlib, third_party, internal]):
        results.append("无导入")
    return "\n".join(results)


@register_tool(
    name="scan_project",
    description="快速扫描项目目录，统计语言分布、文件数量、总行数，了解项目概况。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="code"
)
def scan_project(path: str = ".") -> str:
    """项目概览扫描"""
    import collections
    if not os.path.isdir(path):
        return f"目录不存在: {path}"

    lang_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".vue": "Vue", ".jsx": "React JSX", ".tsx": "React TSX",
        ".css": "CSS", ".scss": "SCSS", ".html": "HTML",
        ".java": "Java", ".kt": "Kotlin", ".swift": "Swift",
        ".go": "Go", ".rs": "Rust", ".c": "C", ".cpp": "C++",
        ".cxx": "C++", ".h": "C/C++ Header", ".hpp": "C++ Header",
        ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
        ".toml": "TOML", ".ini": "INI", ".cfg": "Config",
        ".md": "Markdown", ".rst": "RST", ".txt": "Text",
        ".sh": "Shell", ".bat": "Batch", ".ps1": "PowerShell",
        ".sql": "SQL", ".dockerfile": "Dockerfile", ".makefile": "Makefile",
    }

    stats = collections.defaultdict(lambda: {"files": 0, "lines": 0})
    total_files = 0
    total_lines = 0

    skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv",
                 "dist", "build", ".tox", ".eggs", "logs", "recordings"}

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if f.endswith("Dockerfile"):
                ext = ".dockerfile"
            elif f == "Makefile":
                ext = ".makefile"
            lang = lang_map.get(ext, f"Other ({ext})")
            fpath = os.path.join(root, f)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
                    line_count = sum(1 for _ in fp)
            except Exception:
                line_count = 0
            stats[lang]["files"] += 1
            stats[lang]["lines"] += line_count
            total_files += 1
            total_lines += line_count

    results = [f"📊 项目扫描: {os.path.abspath(path)}",
               f"   总文件: {total_files} | 总行数: {total_lines:,}\n"]
    for lang, s in sorted(stats.items(), key=lambda x: x[1]["lines"], reverse=True):
        pct = s["lines"] / total_lines * 100 if total_lines else 0
        results.append(f"  {lang:15s}  {s['files']:4d} 文件  {s['lines']:8,d} 行  ({pct:5.1f}%)")
    return "\n".join(results)


@register_tool(
    name="find_references",
    description="在项目中查找对指定符号（函数名/类名/变量名）的所有引用位置。",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "要查找的符号名称"},
            "path": {"type": "string", "description": "项目根目录", "default": "."},
            "file_type": {"type": "string", "description": "限制文件类型，如 '.py'", "default": ".py"},
        },
        "required": ["symbol"]
    },
    category="code"
)
def find_references(symbol: str, path: str = ".", file_type: str = ".py") -> str:
    """在项目中查找符号引用"""
    import re
    results = []
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build")]
        for fname in files:
            if file_type and not fname.endswith(file_type):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
                    for i, line in enumerate(fp, 1):
                        if pattern.search(line):
                            results.append(f"{fpath}:{i}: {line.strip()[:120]}")
            except Exception:
                pass
            if len(results) >= 100:
                break
        if len(results) >= 100:
            break
    return "\n".join(results) if results else f"未找到对 '{symbol}' 的引用"
