"""工具执行入口 — agent_loop 使用"""
from ..tools.registry import execute_tool
from .agent_optimizer import execute_tools_parallel


def _execute_tool_optimized(name: str, args: dict) -> str:
    """单个工具执行（优化版），供 execute_tools_parallel 调用"""
    return execute_tool(name, args)
