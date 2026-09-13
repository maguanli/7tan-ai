"""
独立任务定义 — 从调度器模块分离
详见架构文档 §19.1
"""
from pathlib import Path
from datetime import datetime

from loguru import logger

from ..pipeline.pipeline import Pipeline
from ..pipeline.task_queue import get_task_queue, TaskPriority


def crawl_source(name: str, url: str, site_type: str = "game"):
    """
    爬取单个源站

    Args:
        name: 源站名称
        url: 源站 URL
        site_type: 源站类型 (game/software/both)
    """
    logger.info(f"🕷️ 开始爬取: {name} ({url})")

    pipeline = Pipeline()
    task_desc = (
        f"爬取 {name} 的最新{site_type}资源，检查是否有新版本发布。"
        f"源站URL: {url}。"
        f"按顺序浏览页面，提取{site_type}信息，去重检查，"
        f"如果发现新资源则下载并发布。"
    )

    result = pipeline.run(task=task_desc)

    if result["success"]:
        logger.info(f"✅ {name} 爬取完成")
    else:
        logger.warning(f"⚠️ {name} 爬取失败: {result['result'][:100]}")

    return result


def scheduled_run(task_desc: str):
    """执行定时任务"""
    logger.info(f"▶️ 执行定时任务: {task_desc[:80]}")

    pipeline = Pipeline()
    result = pipeline.run(task=task_desc)

    if result["success"]:
        logger.info(f"✅ 定时任务完成: {task_desc[:50]}")
    else:
        logger.error(f"❌ 定时任务失败: {task_desc[:50]}")

    return result


def health_check_job():
    """定时健康检查"""
    from ..tools.monitor_tools import health_check
    result = health_check()
    logger.info(f"🏥 健康检查: {result}")
    return result


def cleanup_job():
    """定时磁盘清理"""
    from ..utils.helpers import disk_usage_gb

    free_gb = disk_usage_gb(".")
    logger.info(f"🧹 磁盘清理: 可用 {free_gb:.1f}GB")

    # 清理 7 天前的沙盒文件
    count = 0
    sandbox_dir = Path("data/sandbox")
    if sandbox_dir.exists():
        cutoff = datetime.now().timestamp() - 7 * 86400
        for f in sandbox_dir.glob("*.py"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                count += 1

    # 清理过期图片
    from ..config.loader import load_config
    config = load_config()
    retention_days = config.get("storage", {}).get("image_retention_days", 30)

    images_dir = Path("downloads/images")
    if images_dir.exists():
        cutoff_images = datetime.now().timestamp() - retention_days * 86400
        img_count = 0
        for f in images_dir.rglob("*"):
            if f.is_file() and f.stat().st_mtime < cutoff_images:
                f.unlink()
                img_count += 1
        if img_count:
            logger.info(f"🗑️ 清理了 {img_count} 个过期图片")

    # 清理过期日志
    from ..config.loader import load_config
    log_retention = config.get("logging", {}).get("retention", "30 days")
    try:
        retention_num = int(log_retention.split()[0]) if log_retention else 30
    except Exception:
        retention_num = 30

    logs_dir = Path("logs")
    if logs_dir.exists():
        cutoff_logs = datetime.now().timestamp() - retention_num * 86400
        log_count = 0
        for f in logs_dir.glob("*.log*"):
            if f.is_file() and f.stat().st_mtime < cutoff_logs:
                f.unlink()
                log_count += 1
        if log_count:
            logger.info(f"🗑️ 清理了 {log_count} 个过期日志")

    if count == 0:
        logger.info("🧹 无需清理")

    return {"deleted_sandbox": count, "free_gb": free_gb}


def poll_site_job(site: dict):
    """轮询单个源站"""
    name = site.get("name", "unknown")
    url = site.get("url", "")
    site_type = site.get("site_type", "game")

    logger.info(f"🕷️ 轮询源站: {name} ({url})")

    result = crawl_source(name=name, url=url, site_type=site_type)

    if result["success"]:
        logger.info(f"✅ {name} 轮询完成")
    else:
        logger.warning(f"⚠️ {name} 轮询失败: {result['result'][:100]}")

    return result
