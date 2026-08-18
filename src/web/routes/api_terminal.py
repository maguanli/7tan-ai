"""
终端 API — VS Code 扩展集成
POST /api/terminal/execute — 执行编译/构建命令
"""
import subprocess
import os
import threading
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from loguru import logger

router = APIRouter(prefix="/api/terminal", tags=["terminal"])


# ===== 终端命令白名单（安全防护）=====
# 只允许编译/构建/查询类安全命令；白名单外一律拒绝
ALLOWED_PREFIXES = (
    "python ", "python3 ", "pip ", "pip3 ", "py ",
    "node ", "npm ", "pnpm ", "yarn ", "npx ",
    "git status", "git log", "git diff", "git branch", "git remote", "git tag",
    "git add", "git commit", "git stash", "git show", "git blame",
    "dir", "ls", "cd ", "echo ", "type ", "where ", "findstr ", "cls", "ver",
    "javac ", "java -version", "gradle ", "mvn ", "go ", "cargo ", "rustc ",
    "flutter ", "dart ", "adb ", "tasklist", "systeminfo",
    "cmake ", "make ", "ninja ", "cl ", "gcc ", "g++ ", "mingw32-make ",
    "powershell -", "cmd /c ",
)
# 危险命令黑名单（无论前缀，命中即拒绝）
BLOCKED_KEYWORDS = (
    "rm -rf", "del /s", "format ", "taskkill", "shutdown", "reg delete",
    "rd /s", "rmdir /s", "powershell -enc", "certutil", "bitsadmin",
    "wget ", "curl -o", "net user", "net localgroup", "sc delete",
    "attrib -r -s -h", "cipher /w", "fsutil", "diskpart", "vssadmin",
)


def _is_allowed_command(command: str) -> bool:
    """校验终端命令是否在白名单内"""
    cmd = command.strip().lower()
    if not cmd:
        return False
    for kw in BLOCKED_KEYWORDS:
        if kw in cmd:
            return False
    for prefix in ALLOWED_PREFIXES:
        if cmd.startswith(prefix):
            return True
    return False


class TerminalExecuteRequest(BaseModel):
    command: str
    cwd: Optional[str] = None


@router.post("/execute")
async def execute_command(req: TerminalExecuteRequest):
    """执行终端命令并返回输出"""
    if not _is_allowed_command(req.command):
        logger.warning(f"🚫 终端命令不在白名单，已拒绝: {req.command}")
        return {
            "success": False,
            "output": "❌ 命令不在白名单，已拒绝执行（仅允许编译/构建/查询类命令）",
            "exit_code": -1,
        }
    logger.info(f"🖥️ 执行命令: {req.command}")

    try:
        cwd = req.cwd or os.getcwd()

        # Windows 下用 cmd /c 包装
        if os.name == 'nt':
            process = subprocess.Popen(
                ['cmd', '/c', req.command],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=False,
            )
        else:
            process = subprocess.Popen(
                req.command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=True,
            )

        # 读取超时设置为 5 分钟
        output_lines = []
        try:
            stdout, _ = process.communicate(timeout=300)
            output_lines = stdout.split('\n') if stdout else []
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()
            if stdout:
                output_lines = stdout.split('\n')
            output_lines.append('[7Tan] ⚠️ 命令超时 (5分钟)，已强制终止')

        return {
            "success": process.returncode == 0,
            "output": '\n'.join(output_lines[-500:]),  # 最多返回最后 500 行
            "exit_code": process.returncode,
            "line_count": len(output_lines),
        }

    except FileNotFoundError:
        return {
            "success": False,
            "output": f"❌ 命令未找到: {req.command.split()[0] if req.command else req.command}",
            "exit_code": -1,
        }
    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        return {
            "success": False,
            "output": f"❌ 执行错误: {str(e)}",
            "exit_code": -1,
        }
