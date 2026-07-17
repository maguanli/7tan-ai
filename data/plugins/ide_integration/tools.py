
"""
VS Code IDE 集成工具集。
通过 code CLI 打开文件、项目，支持跳转到指定行列。
"""

import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

import subprocess
import os
import json

CODE_PATH = r"C:\Users\Administrator\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd"


def _run_code(*args, timeout: int = 10) -> dict:
    """执行 code 命令"""
    cmd = [CODE_PATH] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace", shell=True)
        return {"success": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}


@register_tool(
    name="vscode_open_file",
    description="在 VS Code 中打开文件，可跳转到指定行列。",
    parameters={
            "file_path": {"type": "string", "description": "文件完整路径"},
            "line": {"type": "integer", "description": "跳转行号（0=不跳转）", "default": 0},
            "column": {"type": "integer", "description": "跳转列号（0=不跳转）", "default": 0}
        },
    category="ide"
)
def vscode_open_file(file_path: str, line: int = 0, column: int = 0) -> str:
    """在 VS Code 中打开文件，可跳转到指定行列。
    
    参数:
        file_path: 文件完整路径
        line: 跳转到第几行 (0=不跳转)
        column: 跳转到第几列 (0=不跳转)
    
    示例:
        vscode_open_file("D:\\7tan\\7tanAI\\src\\ui\\app.py", line=42)
    """
    if not os.path.exists(file_path):
        return f"❌ 文件不存在: {file_path}"
    
    # 转换为绝对路径
    file_path = os.path.abspath(file_path)
    
    # 构建跳转参数
    if line > 0 and column > 0:
        goto = f"{file_path}:{line}:{column}"
    elif line > 0:
        goto = f"{file_path}:{line}"
    else:
        goto = file_path
    
    r = _run_code("--goto", goto)
    if r["success"]:
        pos = f" (第{line}行)" if line > 0 else ""
        return f"✅ VS Code 已打开: {file_path}{pos}"
    return f"❌ 打开失败: {r['stderr']}"


@register_tool(
    name="vscode_open_project",
    description="在 VS Code 中打开项目文件夹。",
    parameters={"project_path": {"type": "string", "description": "项目根目录路径"}},
    category="ide"
)
def vscode_open_project(project_path: str) -> str:
    """在 VS Code 中打开项目文件夹。
    
    参数:
        project_path: 项目根目录路径
    
    示例:
        vscode_open_project("D:\\7tan\\ClassicBlockPuzzle")
    """
    if not os.path.isdir(project_path):
        return f"❌ 目录不存在: {project_path}"
    
    project_path = os.path.abspath(project_path)
    r = _run_code(project_path)
    if r["success"]:
        return f"✅ VS Code 已打开项目: {project_path}"
    return f"❌ 打开失败: {r['stderr']}"


@register_tool(
    name="vscode_open_multi",
    description="在 VS Code 中同时打开多个文件。",
    parameters={"files": {"type": "string", "description": "JSON 数组格式的文件路径列表"}},
    category="ide"
)
def vscode_open_multi(files: str) -> str:
    """在 VS Code 中同时打开多个文件（对比/编辑）。
    
    参数:
        files: 文件路径列表，JSON 数组格式
    
    示例:
        vscode_open_multi('["D:\\\\a.py", "D:\\\\b.py"]')
    """
    try:
        file_list = json.loads(files)
    except:
        return "❌ files 参数需要是 JSON 数组格式"
    
    if not file_list:
        return "❌ 文件列表为空"
    
    args = []
    for f in file_list:
        if not os.path.exists(f):
            return f"❌ 文件不存在: {f}"
        args.append(os.path.abspath(f))
    
    r = _run_code(*args)
    if r["success"]:
        return f"✅ VS Code 已打开 {len(file_list)} 个文件"
    return f"❌ 打开失败: {r['stderr']}"


@register_tool(
    name="vscode_diff",
    description="在 VS Code 中对比两个文件的差异。",
    parameters={
            "file1": {"type": "string", "description": "第一个文件路径"},
            "file2": {"type": "string", "description": "第二个文件路径"}
        },
    category="ide"
)
def vscode_diff(file1: str, file2: str) -> str:
    """在 VS Code 中对比两个文件的差异。
    
    参数:
        file1: 第一个文件路径
        file2: 第二个文件路径
    """
    if not os.path.exists(file1):
        return f"❌ 文件不存在: {file1}"
    if not os.path.exists(file2):
        return f"❌ 文件不存在: {file2}"
    
    r = _run_code("--diff", os.path.abspath(file1), os.path.abspath(file2))
    if r["success"]:
        return f"✅ VS Code 正在对比:\n  {file1}\n  {file2}"
    return f"❌ 对比失败: {r['stderr']}"


@register_tool(
    name="vscode_list_extensions",
    description="列出 VS Code 已安装的扩展列表。",
    parameters={},
    category="ide"
)
def vscode_list_extensions() -> str:
    """列出 VS Code 已安装的扩展。"""
    r = _run_code("--list-extensions", timeout=15)
    if r["success"]:
        exts = r["stdout"].split("\n")
        return f"🧩 已安装扩展 ({len(exts)} 个):\n" + "\n".join(f"  • {e}" for e in exts if e)
    return f"❌ 获取失败: {r['stderr']}"


@register_tool(
    name="vscode_install_extension",
    description="安装 VS Code 扩展（通过扩展 ID）。",
    parameters={"extension_id": {"type": "string", "description": "扩展 ID，如 ms-python.python"}},
    category="ide"
)
def vscode_install_extension(extension_id: str) -> str:
    """安装 VS Code 扩展。
    
    参数:
        extension_id: 扩展 ID，如 ms-python.python
    
    示例:
        vscode_install_extension("ms-python.python")
    """
    r = _run_code("--install-extension", extension_id, timeout=60)
    if r["success"]:
        return f"✅ 扩展安装成功: {extension_id}"
    return f"❌ 安装失败: {r['stderr']}"
