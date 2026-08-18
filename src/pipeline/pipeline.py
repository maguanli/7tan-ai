"""
资源处理流水线 — 爬取→下载→改写→审核→发布
详见架构文档 §9
"""
import json
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..agent.agent_loop import run_agent_loop
from ..database.db import get_session, Resource, TaskLog


class Pipeline:
    """资源处理流水线 — 串行执行 6 阶段"""

    def __init__(self, config: dict = None):
        if config is None:
            from ..config.loader import load_config
            config = load_config()
        self.config = config

    def run(self, task: str, session_id: str = None, model: str = None) -> dict:
        """
        运行完整流水线

        Args:
            task: 任务描述，如 "抓取3dm最近更新的游戏" 或 "发布资源ID=5"
            session_id: 会话 ID
            model: 指定模型

        Returns:
            {"success": bool, "result": str, "stages": [...]}
        """
        logger.info(f"🚀 启动流水线: {task[:80]}...")

        stages_result = []
        final_success = False

        try:
            # 使用 Agent 循环执行完整流程
            result = run_agent_loop(
                task=task,
                session_id=session_id,
                model_name=model,
                max_iterations=50,
            )

            final_success = result["success"]

            # 解析各阶段
            if result.get("logs"):
                stages_result = _parse_stages(result["logs"])

            # 记录完成
            logger.info(f"{'✅' if final_success else '❌'} 流水线完成: {task[:50]}...")

            return {
                "success": final_success,
                "result": result["result"],
                "stages": stages_result,
                "cost": result.get("cost", 0),
                "iterations": result.get("iterations", 0),
            }

        except Exception as e:
            logger.error(f"❌ 流水线异常: {e}")
            return {
                "success": False,
                "result": str(e),
                "stages": stages_result,
                "cost": 0,
                "iterations": 0,
            }

    def run_resource(self, resource_id: int, model: str = None) -> dict:
        """处理单个已有资源（补处理）"""
        session = get_session()
        try:
            resource = session.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                return {"success": False, "result": f"资源不存在: ID={resource_id}"}

            task = f"处理资源 ID={resource.id}: {resource.title}\n源URL: {resource.source_url}\n当前状态: {resource.status}"
            return self.run(task=task, model=model)

        finally:
            session.close()


def _parse_stages(logs: list) -> list:
    """解析执行日志中的阶段信息"""
    stages = []
    for log_entry in logs:
        tool_calls = log_entry.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            stages.append({
                "tool": tool_name,
                "args": func.get("arguments", "{}"),
            })
    return stages


def run_single_stage(stage: str, resource: dict, model: str = None) -> dict:
    """执行单个处理阶段（供外部调用）"""
    pipeline = Pipeline()

    stage_prompts = {
        "scrape": f"从以下源站爬取资源: {json.dumps(resource, ensure_ascii=False)}",
        "download": f"下载资源文件: {json.dumps(resource, ensure_ascii=False)}",
        "rewrite": f"改写以下资源简介为7坛风格: {json.dumps(resource, ensure_ascii=False)}",
        "review": f"审核以下发布内容: {json.dumps(resource, ensure_ascii=False)}",
        "upload": f"上传资源文件到云存储: {json.dumps(resource, ensure_ascii=False)}",
        "publish": f"发布资源到7坛网站: {json.dumps(resource, ensure_ascii=False)}",
    }

    task = stage_prompts.get(stage, f"执行{stage}阶段: {json.dumps(resource, ensure_ascii=False)}")
    return pipeline.run(task=task, model=model)
