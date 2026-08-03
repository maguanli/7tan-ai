"""
重构工具插件 — 符号重命名、函数提取、导入整理
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os
import re


@register_tool(
    name="rename_symbol",
    description="在项目中安全地重命名符号（函数名/类名/变量名），列出所有将被修改的位置和内容预览。",
    parameters={
        "type": "object",
        "properties": {
            "old_name": {"type": "string", "description": "旧的符号名"},
            "new_name": {"type": "string", "description": "新的符号名"},
            "path": {"type": "string", "description": "项目根目录", "default": "."},
            "file_type": {"type": "string", "description": "限定的文件后缀", "default": ".py"},
        },
        "required": ["old_name", "new_name"]
    },
    category="refactor"
)
def rename_symbol(old_name: str, new_name: str, path: str = ".",
                  file_type: str = ".py") -> str:
    """预览符号重命名的所有影响位置"""
    changes = []
    pattern = re.compile(rf"\b{re.escape(old_name)}\b")
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv")]
        for fname in files:
            if not fname.endswith(file_type):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as fp:
                    content = fp.read()
                matches = [(m.start(), m.group()) for m in pattern.finditer(content)]
                if matches:
                    lines = content.split("\n")
                    for pos, _ in matches[:3]:  # 每文件最多3处
                        line_no = content[:pos].count("\n") + 1
                        line = lines[line_no - 1].strip()
                        changes.append(f"  {fpath}:{line_no}: {line[:100]}")
                if len([m for m in pattern.finditer(content)]) > 3:
                    changes.append(f"  ... 还有更多")
            except Exception:
                pass
    if not changes:
        return f"未找到 '{old_name}' 的引用"
    return (f"📝 重命名 '{old_name}' → '{new_name}' 将影响 {len(changes)} 处:\n" +
            "\n".join(changes) +
            "\n\n⚠️ 这是预览模式。请使用 file_replace 工具执行替换，或确认后让我来改。")


@register_tool(
    name="organize_imports",
    description="检查 Python 文件的导入语句，按标准库→第三方→内部排序，移除未使用的导入。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
        },
        "required": ["file_path"]
    },
    category="refactor"
)
def organize_imports(file_path: str) -> str:
    """整理导入语句"""
    import ast
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        return f"解析失败: {e}"

    imports = {"stdlib": [], "third_party": [], "internal": []}
    stdlib_names = {"os", "sys", "re", "json", "time", "datetime", "pathlib",
                    "typing", "abc", "collections", "subprocess", "threading",
                    "dataclasses", "enum", "ast", "logging", "io"}

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            name = node.names[0].name
            top = name.split(".")[0]
            if top in stdlib_names:
                imports["stdlib"].append(f"import {name}")
            else:
                imports["third_party"].append(f"import {name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = ", ".join(n.alias or n.name for n in node.names)
            line = f"from {mod} import {names}"
            top = mod.split(".")[0]
            if top in stdlib_names or not top:
                imports["stdlib"].append(line)
            elif top.startswith("src") or node.level > 0:
                imports["internal"].append(line)
            else:
                imports["third_party"].append(line)

    result = []
    for cat in ["stdlib", "third_party", "internal"]:
        if imports[cat]:
            result.extend(sorted(imports[cat]))
            result.append("")
    return "\n".join(result) if result else "无导入语句"


@register_tool(
    name="extract_function",
    description="分析选中的代码块，判断是否适合提取为独立函数，并生成建议的函数签名。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
            "start_line": {"type": "integer", "description": "起始行号"},
            "end_line": {"type": "integer", "description": "结束行号"},
        },
        "required": ["file_path", "start_line", "end_line"]
    },
    category="refactor"
)
def extract_function(file_path: str, start_line: int, end_line: int) -> str:
    """分析代码块提取为函数的可行性"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        block_lines = lines[start_line - 1:end_line]
        block = "".join(block_lines)
    except Exception as e:
        return f"读取失败: {e}"

    # 检测代码块使用的变量
    import ast
    try:
        tree = ast.parse(block)
    except SyntaxError:
        return "代码块语法不正确，无法分析。请确保选中的是完整的语句块。"

    # 分析输入输出变量
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)

    result = [f"📦 代码块分析 ({start_line}-{end_line} 行, {len(block_lines)} 行):",
              f"\n提取的函数建议格式：",
              f"```python",
              f"def extracted_function():  # ← AI 请根据逻辑命名",
              f"    \"\"\"函数功能描述\"\"\"",
              f"    # ... (选中的代码)",
              f"```",
              f"\n代码块引用的变量: {', '.join(sorted(names)) if names else '无外部引用'}"]
    return "\n".join(result)


@register_tool(
    name="format_code",
    description="使用 autopep8/black 格式化 Python 代码，或 prettier 格式化 JS/CSS/HTML。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "文件路径"},
            "formatter": {"type": "string", "description": "格式化工具: auto(默认)/black/autopep8/prettier", "default": "auto"},
        },
        "required": ["file_path"]
    },
    category="refactor"
)
def format_code(file_path: str, formatter: str = "auto") -> str:
    """格式化代码文件"""
    import subprocess
    import sys as _sys
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()
    original = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception as e:
        return f"读取失败: {e}"

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def _run(cmd, timeout=60):
        try:
            return subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout, creationflags=flags,
                                  encoding="utf-8", errors="replace")
        except Exception:
            return None

    if ext == ".py":
        # 优先 python -m black（兼容打包/独立环境 PATH 缺失），逐级回退
        candidates = [
            [_sys.executable, "-m", "black", "-q", file_path],
            ["black", "-q", file_path],
            [_sys.executable, "-m", "autopep8", "--in-place", "--aggressive", file_path],
            ["autopep8", "--in-place", "--aggressive", file_path],
        ]
        for cmd in candidates:
            r = _run(cmd)
            if r is not None and r.returncode == 0:
                with open(file_path, "r", encoding="utf-8") as f:
                    new = f.read()
                if new != original:
                    return f"✅ 已格式化 ({' '.join(cmd[:-1])}): {file_path}"
                return f"✅ 无需格式化: {file_path}"
        # 全部失败 → 自动安装 black 并重试一次
        inst = _run([_sys.executable, "-m", "pip", "install", "black", "-q"], timeout=180)
        if inst is not None and inst.returncode == 0:
            r = _run([_sys.executable, "-m", "black", "-q", file_path])
            if r is not None and r.returncode == 0:
                with open(file_path, "r", encoding="utf-8") as f:
                    new = f.read()
                if new != original:
                    return f"✅ 已格式化 (black 自动安装后): {file_path}"
                return f"✅ 无需格式化: {file_path}"
        return "⚠️ 未安装格式化工具（black/autopep8），自动安装失败。请手动执行: pip install black"
    elif ext in (".js", ".ts", ".jsx", ".tsx", ".css", ".html", ".json"):
        for cmd in [["npx", "--yes", "prettier", "--write", file_path],
                     ["prettier", "--write", file_path]]:
            r = _run(cmd, timeout=120)
            if r is not None and r.returncode == 0:
                return f"✅ 已格式化 (prettier): {file_path}"
        return "⚠️ 未安装 Prettier。请安装: npm install -g prettier"
    return f"不支持的文件类型: {ext}"
