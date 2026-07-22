"""
文档生成插件 — AI 辅助生成 docstring、README、API 文档
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os


@register_tool(
    name="generate_docstring",
    description="为 Python 文件中缺少文档字符串的函数/类，生成 Google 风格 docstring 模板。AI 应在调用后根据代码逻辑填充模板内容。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
        },
        "required": ["file_path"]
    },
    category="doc"
)
def generate_docstring(file_path: str) -> str:
    """扫描文件，列出所有缺少 docstring 的函数"""
    import ast
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        return f"解析失败: {e}"

    missing = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not ast.get_docstring(node):
                args = [a.arg for a in node.args.args]
                returns = "None" if node.returns else "?"
                if node.returns:
                    returns = ast.unparse(node.returns)
                template = (f'    """\n'
                           f'    {node.name} 的功能描述。\n\n'
                           f'    Args:\n') + \
                           '\n'.join(f'        {a}: {a} 参数说明' for a in args) + \
                           (f'\n\n    Returns:\n        {returns}: 返回值说明' if returns != "None" else "") + \
                           '\n    """'
                missing.append(f"  行 {node.lineno} | def {node.name}({', '.join(args)})")
                missing.append(template)
                missing.append("")
        elif isinstance(node, ast.ClassDef):
            if not ast.get_docstring(node):
                missing.append(f"  行 {node.lineno} | class {node.name}")
                missing.append(f'    """\n    {node.name} 类的功能描述。\n    """')
                missing.append("")
    if not missing:
        return "✅ 所有函数和类都有文档字符串。"
    return "\n".join(missing)


@register_tool(
    name="generate_readme",
    description="扫描项目结构，生成 README.md 模板（包含项目名、安装、使用、结构等占位符）。AI 应填充内容。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
            "project_name": {"type": "string", "description": "项目名称", "default": ""},
        },
        "required": []
    },
    category="doc"
)
def generate_readme(path: str = ".", project_name: str = "") -> str:
    """生成 README 模板"""
    if not os.path.isdir(path):
        return f"目录不存在: {path}"
    name = project_name or os.path.basename(os.path.abspath(path))
    files = os.listdir(path)
    lang = "?"
    if "requirements.txt" in files or "setup.py" in files or "pyproject.toml" in files:
        lang = "Python"
    elif "package.json" in files:
        lang = "JavaScript/TypeScript"
    elif "go.mod" in files:
        lang = "Go"
    elif "Cargo.toml" in files:
        lang = "Rust"

    deps_section = ""
    if "requirements.txt" in files:
        deps_section = "```bash\npip install -r requirements.txt\n```"
    elif "package.json" in files:
        if "yarn.lock" in files:
            deps_section = "```bash\nyarn install\n```"
        else:
            deps_section = "```bash\nnpm install\n```"

    template = f"""# {name}

[项目简介 — AI 请在此填写]

## 技术栈

- 语言: {lang}
[AI 请补充其他技术栈]

## 安装

```bash
git clone [仓库地址]
cd {name}
```
{deps_section}

## 使用

[AI 请在此填写使用示例]

## 项目结构

```
[AI 请在此填写目录树]
```

## 开发

[AI 请在此填写开发指南]
"""
    return template


@register_tool(
    name="analyze_api_routes",
    description="分析 FastAPI/Flask/Express 项目中的 API 路由定义，列出所有端点和方法。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="doc"
)
def analyze_api_routes(path: str = ".") -> str:
    """分析 API 路由"""
    import re
    routes = []
    route_patterns = [
        (r'@(?:app|router)\.(get|post|put|delete|patch|options|head)\(["\']([^"\']+)', "FastAPI"),
        (r'@(?:app|bp)\.route\(["\']([^"\']+)["\'],\s*methods=\[([^\]]+)\]', "Flask"),
        (r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)', "Express"),
    ]

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv")]
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
                    for i, line in enumerate(fp, 1):
                        for pattern, framework in route_patterns:
                            m = re.search(pattern, line.strip())
                            if m:
                                if framework == "Flask":
                                    ep = m.group(1)
                                    methods = m.group(2)
                                else:
                                    methods = m.group(1).upper()
                                    ep = m.group(2)
                                routes.append(f"  [{methods:7s}] {ep:40s} → {fname}:{i} ({framework})")
            except Exception:
                pass
    if not routes:
        return "未发现 API 路由定义"
    return "\n".join(sorted(routes))
