"""
定时任务调度器 — 基于 APScheduler
使用 jobs.py 中定义的任务函数
详见架构文档 §14
"""
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from .jobs import scheduled_run, health_check_job, cleanup_job, poll_site_job

_scheduler: BackgroundScheduler = None


def get_scheduler() -> BackgroundScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )
    return _scheduler


def start_scheduler(config: dict = None):
    """启动调度器"""
    if config is None:
        from ..config.loader import load_config
        config = load_config()

    sched = get_scheduler()
    sched_cfg = config.get("scheduler", {})

    # 清理旧任务
    sched.remove_all_jobs()

    # 添加定时任务
    if sched_cfg.get("auto_publish", True):
        _add_cron_jobs(sched, sched_cfg)
        _add_interval_jobs(sched, sched_cfg)
        _add_site_polling_jobs(sched, config)

    if not sched.running:
        sched.start()
        logger.info("⏰ 调度器已启动")


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("⏰ 调度器已停止")


def _add_cron_jobs(sched: BackgroundScheduler, cfg: dict):
    """添加 Cron 定时任务 — 使用 jobs.py 中的 scheduled_run"""
    cron_jobs = cfg.get("cron_jobs", [])
    # 兼容 dict 格式 (key=job_name) 和 list 格式 [{name, cron}]
    if isinstance(cron_jobs, dict):
        cron_jobs = [{"name": k, **v} for k, v in cron_jobs.items()]
    for item in cron_jobs:
        job_name = item.get("name", "unknown")
        cron = item.get("cron", "")
        task = item.get("task", job_name)

        if not cron:
            continue

        try:
            trigger = CronTrigger.from_crontab(cron, timezone="Asia/Shanghai")
            sched.add_job(
                scheduled_run,
                trigger=trigger,
                args=[task],
                id=job_name,
                name=job_name,
            )
            logger.info(f"📅 定时任务: {job_name} ({cron}) -> {task}")
        except Exception as e:
            logger.error(f"❌ 添加定时任务失败 {job_name}: {e}")


def _add_interval_jobs(sched: BackgroundScheduler, cfg: dict):
    """添加间隔任务（健康检查等）"""
    if cfg.get("health_check", False):
        sched.add_job(
            health_check_job,
            trigger=CronTrigger(minute="*/30", timezone="Asia/Shanghai"),
            id="health_check",
            name="健康检查",
        )

    if cfg.get("cleanup", False):
        sched.add_job(
            cleanup_job,
            trigger=CronTrigger(hour="3", minute="0", timezone="Asia/Shanghai"),
            id="cleanup",
            name="磁盘清理",
        )


def _add_site_polling_jobs(sched: BackgroundScheduler, config: dict):
    """为每个源站添加轮询任务"""
    sources_cfg = config.get("sources", {})
    if isinstance(sources_cfg, dict):
        sites = sources_cfg.get("sites", [])
    elif isinstance(sources_cfg, list):
        sites = sources_cfg
    else:
        return

    for site in sites:
        if not isinstance(site, dict):
            continue
        if not site.get("enabled", True):
            continue

        interval = site.get("crawl_interval", 3600)
        job_id = f"poll_{site['name']}"

        sched.add_job(
            poll_site_job,
            trigger="interval",
            seconds=interval,
            args=[site],
            id=job_id,
            name=f"轮询 {site['name']}",
        )
        logger.info(f"🕷️ 源站轮询: {site['name']} (每 {interval}s)")


def get_jobs_status() -> list:
    """获取所有调度任务状态"""
    sched = get_scheduler()
    jobs = []
    for job in sched.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    return jobs
