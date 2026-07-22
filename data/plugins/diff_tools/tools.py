"""
差异工具插件 — 增强的 diff、patch、变更分析
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import subprocess
import os


def _find_git():
    for git in ["git", "C:\\Program Files\\Git\\bin\\git.exe"]:
        try:
            r = subprocess.run([git, "--version"], capture_output=True, timeout=5,
                              creationflags=subprocess.CREATE_NO_WINDOW)
            if r.returncode == 0:
                return git
        except Exception:
            pass
    return None


@register_tool(
    name="generate_diff",
    description="生成两个文件或两个目录之间的差异对比（unified diff 格式）。",
    parameters={
        "type": "object",
        "properties": {
            "old_path": {"type": "string", "description": "旧文件/目录路径"},
            "new_path": {"type": "string", "description": "新文件/目录路径"},
            "context": {"type": "integer", "description": "上下文行数", "default": 3},
        },
        "required": ["old_path", "new_path"]
    },
    category="diff"
)
def generate_diff(old_path: str, new_path: str, context: int = 3) -> str:
    """生成文件差异"""
    git = _find_git()
    if git:
        cmd = [git, "diff", "--no-index", f"-U{context}", old_path, new_path]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                              creationflags=subprocess.CREATE_NO_WINDOW)
            out = r.stdout.strip()
            return out if out else "两个文件/目录内容相同"
        except Exception as e:
            return f"diff 失败: {e}"
    # Python 回退
    import difflib
    try:
        with open(old_path, "r", encoding="utf-8", errors="replace") as f:
            old_lines = f.readlines()
        with open(new_path, "r", encoding="utf-8", errors="replace") as f:
            new_lines = f.readlines()
        diff = difflib.unified_diff(old_lines, new_lines,
                                     fromfile=old_path, tofile=new_path,
                                     n=context)
        out = "".join(diff)
        return out if out else "两个文件内容相同"
    except Exception as e:
        return f"diff 失败: {e}"


@register_tool(
    name="check_changes",
    description="检查 Git 工作区中所有未提交的变更（修改/新增/删除文件列表+行数统计）。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径", "default": "."},
        },
        "required": []
    },
    category="diff"
)
def check_changes(repo_path: str = ".") -> str:
    """检查工作区变更"""
    git = _find_git()
    if not git:
        return "未找到 Git"

    results = []
    # 状态
    try:
        r = subprocess.run([git, "-C", repo_path, "status", "--short"],
                          capture_output=True, text=True, timeout=10,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        status = r.stdout.strip()
        results.append("📋 工作区变更:\n" + (status if status else "✅ 工作区干净"))
    except Exception as e:
        return f"git status 失败: {e}"

    # 行数统计
    try:
        r = subprocess.run([git, "-C", repo_path, "diff", "--stat"],
                          capture_output=True, text=True, timeout=10,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        stat = r.stdout.strip()
        if stat:
            results.append("\n📊 变更统计:\n" + stat)
    except Exception:
        pass

    return "\n".join(results)


@register_tool(
    name="compare_branches",
    description="对比两个 Git 分支之间的差异，列出所有不同的文件。",
    parameters={
        "type": "object",
        "properties": {
            "branch1": {"type": "string", "description": "第一个分支名"},
            "branch2": {"type": "string", "description": "第二个分支名", "default": "main"},
            "repo_path": {"type": "string", "description": "Git 仓库路径", "default": "."},
        },
        "required": ["branch1"]
    },
    category="diff"
)
def compare_branches(branch1: str, branch2: str = "main",
                     repo_path: str = ".") -> str:
    """对比分支差异"""
    git = _find_git()
    if not git:
        return "未找到 Git"
    try:
        r = subprocess.run([git, "-C", repo_path, "diff", "--name-status",
                           f"{branch2}...{branch1}"],
                          capture_output=True, text=True, timeout=15,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        out = r.stdout.strip()
        if not out:
            return f"分支 '{branch1}' 和 '{branch2}' 没有差异"
        lines = out.split("\n")
        added = sum(1 for l in lines if l.startswith("A"))
        modified = sum(1 for l in lines if l.startswith("M"))
        deleted = sum(1 for l in lines if l.startswith("D"))
        return (f"📊 {branch1} vs {branch2}:\n"
                f"  新增: {added} | 修改: {modified} | 删除: {deleted}\n\n" + out)
    except Exception as e:
        return f"分支对比失败: {e}"


@register_tool(
    name="resolve_conflict",
    description="检测 Git 合并冲突文件，列出冲突位置和内容（ours vs theirs），辅助 AI 决策。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径", "default": "."},
        },
        "required": []
    },
    category="diff"
)
def resolve_conflict(repo_path: str = ".") -> str:
    """检测合并冲突"""
    git = _find_git()
    if not git:
        return "未找到 Git"

    try:
        r = subprocess.run([git, "-C", repo_path, "diff", "--name-only", "--diff-filter=U"],
                          capture_output=True, text=True, timeout=10,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        files = r.stdout.strip().split("\n") if r.stdout.strip() else []
    except Exception:
        files = []

    if not files:
        return "✅ 没有合并冲突"

    results = [f"⚠️ {len(files)} 个文件有合并冲突:\n"]
    for fpath in files:
        full_path = os.path.join(repo_path, fpath)
        if not os.path.isfile(full_path):
            continue
        results.append(f"\n📄 {fpath}:")
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if line.startswith("<<<<<<<") or line.startswith("=======") or line.startswith(">>>>>>>"):
                        results.append(f"  行 {i}: {line.strip()}")
        except Exception:
            pass
    return "\n".join(results)
