
"""
Git 高级操作插件 — 提供 stash、tag、hooks、contributors 等高级 Git 能力。
与 git_ops 插件互补，不重复注册同名工具。
"""
import subprocess
import os
from pathlib import Path
from loguru import logger


def _run_git(args: list, cwd: str = None) -> tuple:
    """执行 git 命令"""
    cmd = ["git"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd or os.getcwd())
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def git_stash(repo_path: str = ".", action: str = "list", message: str = "") -> str:
    """暂存操作（list/push/pop/apply）
    
    参数:
        repo_path: 仓库路径
        action: 操作类型 - list(查看)/push(暂存)/pop(恢复并删除)/apply(恢复不删除)
        message: 暂存消息（push 时使用）
    """
    args = ["stash", action]
    if action == "push" and message:
        args.extend(["-m", message])
    code, out, err = _run_git(args, repo_path)
    return out if code == 0 else f"❌ {err}"


def git_tag(repo_path: str = ".", action: str = "list", tag_name: str = "", message: str = "") -> str:
    """标签管理（list/create/delete）
    
    参数:
        repo_path: 仓库路径
        action: 操作 - list(列出)/create(创建)/delete(删除)
        tag_name: 标签名（create/delete 时必填）
        message: 标签注释信息
    """
    if action == "list":
        args = ["tag", "-l", "--sort=-creatordate"]
    elif action == "create":
        if not tag_name:
            return "❌ 请指定标签名"
        args = ["tag", "-a", tag_name, "-m", message or tag_name]
    elif action == "delete":
        args = ["tag", "-d", tag_name]
    else:
        return f"❌ 未知操作: {action}"
    code, out, err = _run_git(args, repo_path)
    return out if code == 0 else f"❌ {err}"


def git_remote_info(repo_path: str = ".") -> str:
    """查看远程仓库信息（URL、fetch/push 地址）。"""
    code, out, err = _run_git(["remote", "-v"], repo_path)
    return out if code == 0 else f"❌ {err}"


def git_check_commit_message(message: str) -> str:
    """检查提交信息是否符合 Conventional Commits 规范。
    
    规范格式: type(scope): description
    type: feat/fix/docs/style/refactor/perf/test/build/ci/chore/revert
    """
    import re
    pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([\w\-\.]+\))?!?: .{1,72}$'
    issues = []

    if not message:
        return "❌ 提交信息为空"

    lines = message.strip().split('\n')
    subject = lines[0]

    if not re.match(pattern, subject):
        issues.append(f"⚠️ 标题不符合 Conventional Commits 规范：{subject}")
        issues.append("   格式应为: type(scope): description")
        issues.append("   type 可选: feat/fix/docs/style/refactor/perf/test/build/ci/chore/revert")

    if len(subject) > 72:
        issues.append(f"⚠️ 标题超过 72 字符（当前 {len(subject)}）")

    if len(lines) > 1 and lines[1] != "":
        issues.append("⚠️ 标题和正文之间应有空行")

    if not issues:
        return "✅ 提交信息符合规范"

    return '\n'.join(issues)


def git_init_hooks(repo_path: str = ".") -> str:
    """初始化 Git Hooks（commit-msg hook 检查提交信息格式）。
    
    安装后每次 git commit 都会自动检查提交信息是否符合规范。
    """
    hooks_dir = Path(repo_path) / ".git" / "hooks"
    if not hooks_dir.exists():
        return "❌ 不是有效的 Git 仓库"

    pre_commit_hook = hooks_dir / "commit-msg"
    hook_content = '''#!/bin/bash
# 检查提交信息是否符合 Conventional Commits 规范
COMMIT_MSG=$(cat "$1")
PATTERN="^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\\([\\w\\-\\.]+\\))?!?: .{1,72}"

if ! echo "$COMMIT_MSG" | head -1 | grep -qE "$PATTERN"; then
    echo "❌ 提交信息不符合 Conventional Commits 规范"
    echo "   格式: type(scope): description"
    exit 1
fi
'''

    try:
        pre_commit_hook.write_text(hook_content)
        pre_commit_hook.chmod(0o755)
        return f"✅ Git Hook 已初始化: {pre_commit_hook}"
    except Exception as e:
        return f"❌ 初始化失败: {e}"


def git_contributors(repo_path: str = ".", count: int = 10) -> str:
    """查看贡献者统计（按提交次数排序）。
    
    参数:
        repo_path: 仓库路径
        count: 显示前 N 名贡献者
    """
    args = ["shortlog", "-sn", f"-{count}", "--no-merges"]
    code, out, err = _run_git(args, repo_path)
    return out if code == 0 else f"❌ {err}"


def register(registry_func):
    """注册 Git 高级工具到全局注册表（不与 git_ops 重复）"""
    registry_func(
        name="git_stash",
        description="Git stash 暂存操作：list(查看)/push(暂存)/pop(恢复并删除)/apply(恢复保留)。",
        parameters={
            "repo_path": {"type": "string", "description": "仓库路径", "default": "."},
            "action": {"type": "string", "description": "操作: list/push/pop/apply", "default": "list"},
            "message": {"type": "string", "description": "暂存消息（push时用）", "default": ""}
        },
        category="git"
    )(git_stash)

    registry_func(
        name="git_tag",
        description="Git 标签管理：list(列出)/create(创建)/delete(删除)。",
        parameters={
            "repo_path": {"type": "string", "description": "仓库路径", "default": "."},
            "action": {"type": "string", "description": "操作: list/create/delete", "default": "list"},
            "tag_name": {"type": "string", "description": "标签名", "default": ""},
            "message": {"type": "string", "description": "标签注释信息", "default": ""}
        },
        category="git"
    )(git_tag)

    registry_func(
        name="git_remote_info",
        description="查看 Git 远程仓库信息（URL 列表）。",
        parameters={"repo_path": {"type": "string", "description": "仓库路径", "default": "."}},
        category="git"
    )(git_remote_info)

    registry_func(
        name="git_check_commit_message",
        description="检查提交信息是否符合 Conventional Commits 规范。",
        parameters={"message": {"type": "string", "description": "提交信息文本"}},
        category="git"
    )(git_check_commit_message)

    registry_func(
        name="git_init_hooks",
        description="初始化 Git commit-msg Hook，自动检查提交信息格式。",
        parameters={"repo_path": {"type": "string", "description": "仓库路径", "default": "."}},
        category="git"
    )(git_init_hooks)

    registry_func(
        name="git_contributors",
        description="查看 Git 仓库贡献者统计（按提交次数排名）。",
        parameters={
            "repo_path": {"type": "string", "description": "仓库路径", "default": "."},
            "count": {"type": "integer", "description": "显示前 N 名", "default": 10}
        },
        category="git"
    )(git_contributors)
