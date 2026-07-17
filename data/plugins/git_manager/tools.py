
"""
Git 版本控制插件 — 仓库管理、提交、分支操作
"""
import subprocess
import os
import json
from typing import Optional

def git_init(repo_path: str) -> dict:
    """初始化 Git 仓库"""
    try:
        result = subprocess.run(
            ["git", "init"],
            cwd=repo_path, capture_output=True, text=True, timeout=30
        )
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
    except FileNotFoundError:
        return {"success": False, "stderr": "Git 未安装或不在 PATH 中"}

def git_clone(url: str, target_dir: str, branch: str = "") -> dict:
    """克隆远程仓库"""
    cmd = ["git", "clone", url]
    if branch:
        cmd += ["-b", branch]
    cmd.append(target_dir)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
    except FileNotFoundError:
        return {"success": False, "stderr": "Git 未安装"}

def git_status(repo_path: str) -> dict:
    """查看仓库状态"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path, capture_output=True, text=True, timeout=30
        )
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        return {
            "success": True,
            "branch": branch.stdout.strip(),
            "changed_files": result.stdout.strip().split("\n") if result.stdout.strip() else []
        }
    except Exception as e:
        return {"success": False, "stderr": str(e)}

def git_add(repo_path: str, files: str = ".") -> dict:
    """暂存文件"""
    result = subprocess.run(["git", "add", files], cwd=repo_path, capture_output=True, text=True, timeout=30)
    return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}

def git_commit(repo_path: str, message: str) -> dict:
    """提交变更"""
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path, capture_output=True, text=True, timeout=30
    )
    return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}

def git_push(repo_path: str, remote: str = "origin", branch: str = "") -> dict:
    """推送到远程"""
    cmd = ["git", "push", remote]
    if branch:
        cmd.append(branch)
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=60)
    return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}

def git_pull(repo_path: str, remote: str = "origin", branch: str = "") -> dict:
    """拉取远程更新"""
    cmd = ["git", "pull", remote]
    if branch:
        cmd.append(branch)
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=120)
    return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}

def git_log(repo_path: str, count: int = 20) -> dict:
    """查看提交日志"""
    result = subprocess.run(
        ["git", "log", f"-{count}", "--oneline", "--decorate"],
        cwd=repo_path, capture_output=True, text=True, timeout=30
    )
    return {"success": True, "log": result.stdout.strip().split("\n") if result.stdout.strip() else []}

def git_branches(repo_path: str) -> dict:
    """列出所有分支"""
    result = subprocess.run(
        ["git", "branch", "-a"],
        cwd=repo_path, capture_output=True, text=True, timeout=30
    )
    return {"success": True, "branches": [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]}

def git_checkout(repo_path: str, branch: str, create: bool = False) -> dict:
    """切换/创建分支"""
    cmd = ["git", "checkout"]
    if create:
        cmd.append("-b")
    cmd.append(branch)
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=30)
    return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}

def git_diff(repo_path: str, staged: bool = False) -> dict:
    """查看差异"""
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=30)
    return {"success": True, "diff": result.stdout}
