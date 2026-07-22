"""
测试运行器插件 — 运行测试、覆盖率报告、测试发现
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import subprocess
import os


@register_tool(
    name="run_tests",
    description="运行项目测试。自动检测测试框架（pytest/unittest/jest/mocha/go test/cargo test），运行并返回结果。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
            "test_path": {"type": "string", "description": "指定测试文件/目录（可选）", "default": ""},
            "verbose": {"type": "boolean", "description": "详细输出", "default": False},
        },
        "required": []
    },
    category="test"
)
def run_tests(path: str = ".", test_path: str = "", verbose: bool = False) -> str:
    """运行测试"""
    if not os.path.isdir(path):
        return f"目录不存在: {path}"

    files = os.listdir(path)
    extra = ["-v"] if verbose else []

    # Python: pytest
    if os.path.isfile(os.path.join(path, "pytest.ini")) or \
       os.path.isfile(os.path.join(path, "pyproject.toml")):
        cmd = [sys.executable, "-m", "pytest"]
        if test_path:
            cmd.append(test_path)
        cmd += extra + ["--tb=short"]
        return _exec(cmd, cwd=path, timeout=300)
    # Python: unittest
    if test_path:
        cmd = [sys.executable, "-m", "unittest", test_path]
        if verbose:
            cmd.append("-v")
        return _exec(cmd, cwd=path, timeout=300)
    # Node: jest
    if os.path.isfile(os.path.join(path, "jest.config.js")) or \
       os.path.isfile(os.path.join(path, "jest.config.ts")):
        cmd = ["npx", "jest"] + extra
        if test_path:
            cmd.append(test_path)
        return _exec(cmd, cwd=path, timeout=300)
    # Go
    if os.path.isfile(os.path.join(path, "go.mod")):
        cmd = ["go", "test", "./..."]
        if verbose:
            cmd.append("-v")
        return _exec(cmd, cwd=path, timeout=300)
    # Rust
    if os.path.isfile(os.path.join(path, "Cargo.toml")):
        cmd = ["cargo", "test"]
        if verbose:
            cmd.append("--")
        return _exec(cmd, cwd=path, timeout=600)

    return "未检测到已知的测试框架。请使用 run_command 手动运行测试。"


@register_tool(
    name="run_coverage",
    description="运行 Python 测试并生成覆盖率报告（使用 pytest-cov）。显示行覆盖率、遗漏行。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
            "source": {"type": "string", "description": "要统计覆盖率的源码目录", "default": "src"},
        },
        "required": []
    },
    category="test"
)
def run_coverage(path: str = ".", source: str = "src") -> str:
    """运行覆盖率测试"""
    if not os.path.isdir(path):
        return f"目录不存在: {path}"
    cmd = [sys.executable, "-m", "pytest",
           f"--cov={source}", "--cov-report=term-missing",
           "-q", path]
    return _exec(cmd, cwd=path, timeout=300)


@register_tool(
    name="discover_tests",
    description="发现项目中的所有测试文件和测试函数，列出测试组织结构。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="test"
)
def discover_tests(path: str = ".") -> str:
    """发现测试"""
    if not os.path.isdir(path):
        return f"目录不存在: {path}"

    test_files = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv")]
        for fname in files:
            if fname.startswith("test_") and fname.endswith(".py"):
                test_files.append(os.path.join(root, fname))
            elif fname.endswith("_test.py"):
                test_files.append(os.path.join(root, fname))
            elif "test" in fname.lower() and fname.endswith((".js", ".ts", ".go", ".rs")):
                test_files.append(os.path.join(root, fname))

    if not test_files:
        return "未发现测试文件"

    results = [f"📋 发现 {len(test_files)} 个测试文件:\n"]
    for f in sorted(test_files):
        rel = os.path.relpath(f, path)
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fp:
                test_funcs = [l.strip() for l in fp if "def test_" in l and ":" in l]
            results.append(f"  📄 {rel} ({len(test_funcs)} 测试函数)")
        except Exception:
            results.append(f"  📄 {rel}")
    return "\n".join(results)


@register_tool(
    name="generate_test_template",
    description="为指定的 Python 文件/函数生成 pytest 测试模板。AI 应根据函数逻辑填充测试用例。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 源文件路径"},
            "function_name": {"type": "string", "description": "要测试的函数名（可选，不指定则为所有函数生成）", "default": ""},
        },
        "required": ["file_path"]
    },
    category="test"
)
def generate_test_template(file_path: str, function_name: str = "") -> str:
    """生成测试模板"""
    import ast
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        return f"解析失败: {e}"

    bname = os.path.splitext(os.path.basename(file_path))[0]
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            if function_name and node.name != function_name:
                continue
            funcs.append(node)

    if not funcs:
        return "未找到要测试的函数"

    lines = ['"""',
             f'Test suite for {bname}',
             'Auto-generated template — AI should fill in actual test cases.',
             '"""',
             'import pytest',
             f'from {bname} import {", ".join(f.name for f in funcs)}',
             '',
             '']
    for func in funcs:
        lines.append(f'\nclass Test{func.name.title().replace("_", "")}:')
        lines.append(f'    """Tests for {func.name}"""')
        lines.append('')
        lines.append(f'    def test_{func.name}_basic(self):')
        lines.append(f'        """基本功能测试"""')
        lines.append(f'        # Arrange')
        lines.append(f'        # Act')
        lines.append(f'        result = {func.name}()')
        lines.append(f'        # Assert')
        lines.append(f'        assert result is not None  # ← AI 替换为实际断言')
        lines.append('')
        lines.append(f'    def test_{func.name}_edge_cases(self):')
        lines.append(f'        """边界条件测试"""')
        lines.append(f'        # AI 填写边界测试')
        lines.append(f'        pass')
    return "\n".join(lines)


def _exec(cmd: list, cwd: str = None, timeout: int = 120) -> str:
    """执行命令"""
    try:
        import platform
        kw = {"capture_output": True, "text": True, "timeout": timeout,
              "encoding": "utf-8", "errors": "replace"}
        if cwd:
            kw["cwd"] = cwd
        if platform.system() == "Windows":
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        r = subprocess.run(cmd, **kw)
        out = r.stdout.strip()
        if r.stderr.strip():
            out += "\n" + r.stderr.strip()
        if r.returncode == 0:
            return out + "\n\n✅ 通过"
        else:
            return out + f"\n\n❌ 失败 (exit={r.returncode})"
    except subprocess.TimeoutExpired:
        return f"⏱ 超时 ({timeout}秒)"
    except Exception as e:
        return f"❌ 执行失败: {e}"
