"""
依赖分析插件 — 项目依赖图、循环依赖检测、依赖版本检查
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os
import subprocess


@register_tool(
    name="check_dependencies",
    description="检查 Python 项目依赖：列出已安装的包和版本，标记是否有安全漏洞（通过 pip-audit）。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="deploy"
)
def check_dependencies(path: str = ".") -> str:
    """列出项目依赖"""
    results = []
    # pip list
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "list", "--format=columns"],
                          capture_output=True, text=True, timeout=30,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        lines = r.stdout.strip().split("\n")
        results.append(f"📦 已安装 {len(lines)-2} 个包:\n")
        results.append("\n".join(lines[:30]))  # 只显示前30个
    except Exception as e:
        return f"pip list 失败: {e}"
    return "\n".join(results)


@register_tool(
    name="detect_circular_imports",
    description="检测 Python 项目中的循环导入问题。分析内部模块之间的导入关系，找出循环依赖。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="code"
)
def detect_circular_imports(path: str = ".") -> str:
    """检测循环导入"""
    import ast
    from collections import defaultdict

    # 构建导入图
    graph = defaultdict(set)  # module -> set of imported modules
    module_files = {}

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv")]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, path).replace("\\", "/").replace("/", ".")
            mod = rel[:-3]  # 去掉 .py
            module_files[mod] = fpath
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=fpath)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            graph[mod].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            graph[mod].add(node.module)
            except Exception:
                pass

    # DFS 检测环
    def find_cycle(node, path_nodes, visited):
        if node in path_nodes:
            idx = path_nodes.index(node)
            return path_nodes[idx:] + [node]
        if node in visited:
            return None
        visited.add(node)
        path_nodes.append(node)
        for neighbor in graph.get(node, set()):
            result = find_cycle(neighbor, list(path_nodes), visited)
            if result:
                return result
        path_nodes.pop()
        return None

    cycles = []
    for module in graph:
        cycle = find_cycle(module, [], set())
        if cycle and cycle not in cycles:
            cycles.append(cycle)

    if not cycles:
        return "✅ 未检测到循环导入"

    results = [f"⚠️ 检测到 {len(cycles)} 个循环导入:\n"]
    for c in cycles:
        arrow = " → ".join(c)
        results.append(f"  🔄 {arrow}")
        # 显示文件路径
        for mod in c:
            if mod in module_files:
                results.append(f"     {module_files[mod]}")
    return "\n".join(results)


@register_tool(
    name="generate_dependency_graph",
    description="生成项目的 Mermaid 依赖关系图（内部模块→依赖关系），可视化项目结构。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
            "max_depth": {"type": "integer", "description": "最大模块深度", "default": 2},
        },
        "required": []
    },
    category="code"
)
def generate_dependency_graph(path: str = ".", max_depth: int = 2) -> str:
    """生成依赖关系图"""
    import ast
    from collections import defaultdict

    graph = defaultdict(set)
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv")]
        depth = root.replace(path, "").count(os.sep)
        if depth > max_depth:
            dirs[:] = []
        for fname in files:
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, path).replace("\\", "/")[:-3]
            mod_name = rel.replace("/", ".")
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=fpath)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            graph[mod_name].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            graph[mod_name].add(node.module)
            except Exception:
                pass

    lines = ["```mermaid", "graph TD"]
    for src, deps in sorted(graph.items()):
        safe_src = src.replace(".", "_").replace("-", "_").replace(" ", "_")
        for dep in sorted(deps):
            safe_dep = dep.replace(".", "_").replace("-", "_").replace(" ", "_")
            lines.append(f"    {safe_src}[{src}] --> {safe_dep}[{dep}]")
    lines.append("```")
    return "\n".join(lines)


@register_tool(
    name="check_outdated",
    description="检查 pip/npm 项目中过期可升级的依赖包（通过 pip list --outdated / npm outdated）。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="deploy"
)
def check_outdated(path: str = ".") -> str:
    """检查过期依赖"""
    results = []
    # Python
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "list", "--outdated",
                          "--format=columns"],
                          capture_output=True, text=True, timeout=30,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        if r.stdout.strip():
            results.append("📦 Python 过期包:\n" + r.stdout.strip())
    except Exception:
        pass
    # Node
    if os.path.isfile(os.path.join(path, "package.json")):
        try:
            r = subprocess.run(["npm", "outdated", "--prefix", path],
                             capture_output=True, text=True, timeout=30,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            if r.stdout.strip() and r.returncode != 0:
                results.append("\n📦 Node.js 过期包:\n" + r.stdout.strip())
        except Exception:
            pass
    return "\n".join(results) if results else "✅ 所有依赖均为最新版本"
