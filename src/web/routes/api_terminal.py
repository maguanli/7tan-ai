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


class TerminalExecuteRequest(BaseModel):
    command: str
    cwd: Optional[str] = None


@router.post("/execute")
async def execute_command(req: TerminalExecuteRequest):
    """执行终端命令并返回输出"""
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
