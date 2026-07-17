"""
Git 版本控制操作工具集 — 标准 @register_tool 注册
支持 git status、diff、commit、push、pull、branch、log、clone、init 等操作。
"""
import sys
import os
from pathlib import Path
from typing import Optional

# ========== 标准工具注册 ==========
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

GIT_PATH = r"C:\Program Files\Git\bin\git.exe"


def _run_git(repo_path: str, *args, timeout: int = 30) -> dict:
    """在指定仓库中执行 git 命令，返回 {success, stdout, stderr}"""
    if not os.path.exists(repo_path):
        return {"success": False, "stdout": "", "stderr": f"仓库路径不存在: {repo_path}"}

    cmd = [GIT_PATH, "-C", repo_path] + list(args)
    try:
        import subprocess
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
        return {
            "success": r.returncode == 0,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
            "returncode": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "命令执行超时"}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}


@register_tool(
    name="git_status",
    description="查看 Git 仓库状态：已修改、已暂存、未跟踪的文件。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库本地路径"},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_status(repo_path: str) -> str:
    """查看 Git 仓库状态"""
    r = _run_git(repo_path, "status", "--short")
    if not r["success"]:
        return f"❌ Git status 失败:\n{r['stderr']}"
    output = r["stdout"]
    if not output:
        return "✅ 工作区干净，无变更。"

    lines = output.split("\n")
    staged = [l for l in lines if l[0] != " " and l[:2].strip()]
    unstaged = [l for l in lines if l[0] == " " and l[1] != " "]
    untracked = [l for l in lines if l.startswith("??")]

    result = f"📊 Git 状态 (共 {len(lines)} 项变更):\n"
    if staged:
        result += f"\n📦 已暂存 ({len(staged)}):\n"
        for l in staged:
            result += f"  {l}\n"
    if unstaged:
        result += f"\n✏️ 未暂存 ({len(unstaged)}):\n"
        for l in unstaged:
            result += f"  {l}\n"
    if untracked:
        result += f"\n❓ 未跟踪 ({len(untracked)}):\n"
        for l in untracked:
            result += f"  {l}\n"
    return result


@register_tool(
    name="git_diff",
    description="查看 Git 工作区或暂存区差异。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "staged": {"type": "boolean", "description": "True=查看已暂存差异，默认False=未暂存", "default": False},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_diff(repo_path: str, staged: bool = False) -> str:
    """查看 Git 差异"""
    args = ["diff"]
    if staged:
        args.append("--staged")
    r = _run_git(repo_path, *args, timeout=60)
    if not r["success"]:
        return f"❌ Git diff 失败:\n{r['stderr']}"
    output = r["stdout"]
    if not output:
        return "✅ 无差异。"
    if len(output) > 8000:
        output = output[:8000] + "\n... (输出过长，已截断)"
    return f"📝 Git Diff:\n```diff\n{output}\n```"


@register_tool(
    name="git_log",
    description="查看 Git 提交历史（含 ASCII 图表）。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "count": {"type": "integer", "description": "显示最近 N 条", "default": 10},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_log(repo_path: str, count: int = 10) -> str:
    """查看提交历史"""
    r = _run_git(repo_path, "log", f"-{count}", "--oneline", "--decorate", "--graph")
    if not r["success"]:
        return f"❌ Git log 失败:\n{r['stderr']}"
    output = r["stdout"]
    if not output:
        return "📭 暂无提交记录。"
    return f"📜 最近 {count} 条提交:\n```\n{output}\n```"


@register_tool(
    name="git_commit",
    description="提交暂存区变更。建议使用 Conventional Commits 格式：feat:/fix:/chore:",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "message": {"type": "string", "description": "提交信息"},
        },
        "required": ["repo_path", "message"],
    },
    category="git",
)
def git_commit(repo_path: str, message: str) -> str:
    """提交变更"""
    s = _run_git(repo_path, "diff", "--staged", "--name-only")
    if not s["stdout"]:
        return "⚠️ 暂存区为空，请先用 git_add 添加文件。"

    r = _run_git(repo_path, "commit", "-m", message)
    if r["success"]:
        return f"✅ 提交成功!\n{r['stdout']}"
    return f"❌ 提交失败:\n{r['stderr']}"


@register_tool(
    name="git_add",
    description="将文件添加到 Git 暂存区。默认 '.' 添加所有变更。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "files": {"type": "string", "description": "要添加的文件（默认 '.' 添加全部）", "default": "."},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_add(repo_path: str, files: str = ".") -> str:
    """暂存文件"""
    r = _run_git(repo_path, "add", files)
    if r["success"]:
        return f"✅ 已暂存: {files}"
    return f"❌ 暂存失败:\n{r['stderr']}"


@register_tool(
    name="git_push",
    description="推送提交到远程仓库。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "remote": {"type": "string", "description": "远程名称，默认 origin", "default": "origin"},
            "branch": {"type": "string", "description": "分支名（可选，默认当前分支）", "default": ""},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_push(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    """推送到远程"""
    args = ["push", remote]
    if branch:
        args.append(branch)
    r = _run_git(repo_path, *args, timeout=120)
    if r["success"]:
        return f"✅ 推送成功!\n{r['stdout']}"
    return f"❌ 推送失败:\n{r['stderr']}"


@register_tool(
    name="git_pull",
    description="从远程仓库拉取更新。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "remote": {"type": "string", "description": "远程名称，默认 origin", "default": "origin"},
            "branch": {"type": "string", "description": "分支名（可选）", "default": ""},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_pull(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    """拉取远程更新"""
    args = ["pull", remote]
    if branch:
        args.append(branch)
    r = _run_git(repo_path, *args, timeout=120)
    if r["success"]:
        return f"✅ 拉取成功!\n{r['stdout']}"
    return f"❌ 拉取失败:\n{r['stderr']}"


@register_tool(
    name="git_branch",
    description="列出所有 Git 分支，高亮当前分支。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_branch(repo_path: str) -> str:
    """列出分支"""
    r = _run_git(repo_path, "branch", "-a")
    if not r["success"]:
        return f"❌ 获取分支失败:\n{r['stderr']}"
    return f"🌿 分支列表:\n```\n{r['stdout']}\n```"


@register_tool(
    name="git_checkout",
    description="切换或创建 Git 分支。create=True 则创建新分支。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "branch": {"type": "string", "description": "目标分支名"},
            "create": {"type": "boolean", "description": "是否创建新分支后切换", "default": False},
        },
        "required": ["repo_path", "branch"],
    },
    category="git",
)
def git_checkout(repo_path: str, branch: str, create: bool = False) -> str:
    """切换/创建分支"""
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch)
    r = _run_git(repo_path, *args)
    if r["success"]:
        action = "创建并切换" if create else "切换"
        return f"✅ {action}到分支 '{branch}' 成功!\n{r['stdout']}"
    return f"❌ 切换失败:\n{r['stderr']}"


@register_tool(
    name="git_clone",
    description="克隆远程仓库到本地。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "远程仓库 URL"},
            "target_dir": {"type": "string", "description": "本地目标路径"},
        },
        "required": ["url", "target_dir"],
    },
    category="git",
)
def git_clone(url: str, target_dir: str) -> str:
    """克隆仓库"""
    parent = os.path.dirname(target_dir) or "."
    r = _run_git(parent, "clone", url, target_dir, timeout=300)
    if r["success"]:
        return f"✅ 克隆成功到 {target_dir}!\n{r['stdout']}"
    return f"❌ 克隆失败:\n{r['stderr']}"


@register_tool(
    name="git_init",
    description="初始化新 Git 仓库。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "要初始化的目录路径"},
        },
        "required": ["repo_path"],
    },
    category="git",
)
def git_init(repo_path: str) -> str:
    """初始化仓库"""
    os.makedirs(repo_path, exist_ok=True)
    r = _run_git(repo_path, "init")
    if r["success"]:
        return f"✅ Git 仓库已初始化: {repo_path}\n{r['stdout']}"
    return f"❌ 初始化失败:\n{r['stderr']}"
