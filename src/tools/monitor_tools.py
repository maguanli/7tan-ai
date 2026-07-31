"""
监控工具 — 费用追踪、健康检查、系统状态
详见架构文档 §15-16
"""
import json
import time
from datetime import datetime
from pathlib import Path

from .registry import register_tool

# 费用记录文件
COST_FILE = Path("data/costs.json")


@register_tool(
    name="track_cost",
    description="记录一次 AI 调用费用。每次调用 LLM 后必须调用此工具记录。",
    parameters={
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "模型名称"},
            "prompt_tokens": {"type": "integer", "description": "输入 token 数"},
            "completion_tokens": {"type": "integer", "description": "输出 token 数"},
            "cost": {"type": "number", "description": "费用（人民币元）"},
            "task_type": {"type": "string", "description": "任务类型: scrape/rewrite/review/publish"},
        },
        "required": ["model", "prompt_tokens", "completion_tokens"]
    },
    category="monitor",
)
def track_cost(model: str, prompt_tokens: int, completion_tokens: int,
               cost: float = 0.0, task_type: str = "") -> str:
    """记录 AI 费用"""
    COST_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 自动计算费用（如果未提供）
    if cost == 0.0:
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)

    record = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost": round(cost, 6),
        "task_type": task_type,
    }

    # 追加到文件
    records = []
    if COST_FILE.exists():
        try:
            records = json.loads(COST_FILE.read_text())
        except Exception:
            records = []
    records.append(record)
    COST_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2))

    total = sum(r["cost"] for r in records)
    return f"💰 费用已记录: ¥{cost:.4f} (累计: ¥{total:.4f})"


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """估算费用（人民币）"""
    # 价格参考（每百万 token，人民币）
    prices = {
        # DeepSeek
        "deepseek-v4-pro": (3.0, 6.0),
        "deepseek-v4-flash": (1.0, 2.0),
        "deepseek-reasoner": (4.0, 16.0),
        # OpenAI
        "gpt-4o": (18.5, 55.5),
        "gpt-4o-mini": (1.1, 3.7),
        "gpt-4-turbo": (74.0, 222.0),
        # SiliconFlow (硅基流动)
        "Qwen/Qwen2.5-7B-Instruct": (0.35, 0.35),
        "Qwen/Qwen2.5-72B-Instruct": (4.0, 4.0),
        "deepseek-ai/DeepSeek-V3": (2.0, 4.0),
        # 豆包 (Doubao/字节)
        "doubao-pro-32k": (0.8, 2.0),
        "doubao-lite-32k": (0.3, 0.6),
        # 阿里通义千问
        "qwen-turbo": (0.3, 0.6),
        "qwen-plus": (0.8, 2.0),
        "qwen-max": (2.8, 8.4),
        # Ollama (免费本地)
        "llama3": (0.0, 0.0),
        "mistral": (0.0, 0.0),
    }

    input_price, output_price = prices.get(model, (1.0, 2.0))
    input_cost = (prompt_tokens / 1_000_000) * input_price
    output_cost = (completion_tokens / 1_000_000) * output_price
    return input_cost + output_cost


@register_tool(
    name="get_cost_report",
    description="获取费用报告：按日期/任务类型汇总费用。",
    parameters={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "统计最近 N 天", "default": 7},
        },
        "required": []
    },
    category="monitor",
)
def get_cost_report(days: int = 7) -> dict:
    """获取费用报告 — 返回 dict 用于 API"""
    result = {
        "total_cost": 0.0,
        "total_tokens": 0,
        "total_calls": 0,
        "by_model": {},
        "by_task_type": {},
        "daily_breakdown": [],
    }

    if not COST_FILE.exists():
        return result

    try:
        from json import loads
        records = loads(COST_FILE.read_text())
    except Exception:
        return result

    cutoff = datetime.now().timestamp() - days * 86400
    recent = []
    for r in records:
        ts = datetime.fromisoformat(r["timestamp"]).timestamp()
        if ts >= cutoff:
            recent.append(r)

    if not recent:
        return result

    result["total_calls"] = len(recent)
    result["total_cost"] = round(sum(r["cost"] for r in recent), 4)
    result["total_tokens"] = sum(r["total_tokens"] for r in recent)

    # 按模型汇总
    for r in recent:
        model = r["model"]
        result["by_model"].setdefault(model, {"cost": 0.0, "tokens": 0, "calls": 0})
        result["by_model"][model]["cost"] = round(result["by_model"][model]["cost"] + r["cost"], 4)
        result["by_model"][model]["tokens"] += r["total_tokens"]
        result["by_model"][model]["calls"] += 1

    # 按任务类型汇总
    for r in recent:
        tt = r.get("task_type", "unknown")
        result["by_task_type"].setdefault(tt, {"cost": 0.0, "calls": 0})
        result["by_task_type"][tt]["cost"] = round(result["by_task_type"][tt]["cost"] + r["cost"], 4)
        result["by_task_type"][tt]["calls"] += 1

    # 每日明细
    from collections import defaultdict
    daily = defaultdict(lambda: {"date": "", "model_cost": 0.0, "download_cost": 0.0, "storage_cost": 0.0, "total": 0.0})
    for r in recent:
        date_str = r["timestamp"][:10]
        daily[date_str]["date"] = date_str
        if r.get("task_type") in ("scrape", "download"):
            daily[date_str]["download_cost"] = round(daily[date_str]["download_cost"] + r["cost"], 4)
        elif r.get("task_type") in ("rewrite", "review"):
            daily[date_str]["model_cost"] = round(daily[date_str]["model_cost"] + r["cost"], 4)
        else:
            daily[date_str]["model_cost"] = round(daily[date_str]["model_cost"] + r["cost"], 4)
        daily[date_str]["total"] = round(daily[date_str]["total"] + r["cost"], 4)

    result["daily_breakdown"] = sorted(daily.values(), key=lambda x: x["date"])

    return result


@register_tool(
    name="health_check",
    description="系统健康检查：检查各组件状态（数据库、浏览器、网络、磁盘）。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="monitor",
)
def health_check() -> str:
    """系统健康检查"""
    import shutil
    import requests

    checks = []

    # 1. 数据库
    try:
        from ..database.db import get_engine
        engine = get_engine()
        engine.connect().close()
        checks.append("✅ 数据库: 正常")
    except Exception as e:
        checks.append(f"❌ 数据库: {e}")

    # 2. 磁盘空间
    free_gb = shutil.disk_usage(".").free / (1024 ** 3)
    if free_gb > 5:
        checks.append(f"✅ 磁盘: {free_gb:.1f}GB 可用")
    elif free_gb > 1:
        checks.append(f"⚠️ 磁盘不足: {free_gb:.1f}GB")
    else:
        checks.append(f"❌ 磁盘严重不足: {free_gb:.1f}GB")

    # 3. 网络
    try:
        resp = requests.get("https://www.baidu.com", timeout=5)
        checks.append(f"✅ 网络: 正常 ({resp.elapsed.total_seconds():.2f}s)")
    except Exception:
        checks.append("❌ 网络: 不通")

    # 4. 配置文件
    config_exists = Path("config/config.yaml").exists()
    checks.append(f"{'✅' if config_exists else '❌'} 配置文件: {'存在' if config_exists else '缺失'}")

    return "🏥 系统健康检查:\n" + "\n".join(checks)


@register_tool(
    name="get_system_status",
    description="获取系统运行状态：运行时间、资源使用、任务统计。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="monitor",
)
def get_system_status() -> str:
    """获取系统运行状态"""
    import platform

    # 任务统计
    from ..database.db import get_session, Resource, TaskLog
    session = get_session()
    try:
        total_resources = session.query(Resource).count()
        published = session.query(Resource).filter(Resource.status == "published").count()
        failed = session.query(Resource).filter(Resource.status == "failed").count()
        pending = session.query(Resource).filter(Resource.status == "pending").count()

        today = datetime.now().strftime("%Y-%m-%d")
        today_logs = session.query(TaskLog).filter(
            TaskLog.started_at >= today
        ).count()
    finally:
        session.close()

    return (
        f"📊 系统状态\n"
        f"  系统: {platform.system()} {platform.release()}\n"
        f"  Python: {platform.python_version()}\n"
        f"  总资源: {total_resources} (已发布 {published}, 待处理 {pending}, 失败 {failed})\n"
        f"  今日任务: {today_logs} 个\n"
    )
