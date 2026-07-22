"""
配置读写 API
GET  /api/settings         — 获取配置（脱敏）
PUT  /api/settings         — 更新配置
POST /api/settings/restart — 重启程序
"""
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from ...config.loader import load_config, save_config
from ...scheduler.daemon import restart_self
from loguru import logger

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask_secret(value: Any) -> Any:
    """脱敏敏感字段"""
    if isinstance(value, str) and len(value) > 8:
        return value[:3] + "••••" + value[-3:]
    return value


def _update_env_model(ai_key: str, model: str):
    """同步 .env 中的模型环境变量（目前仅 deepseek 使用 ${DEEPSEEK_MODEL} 变量）"""
    if ai_key != "deepseek":
        return
    if not model or "••••" in str(model):
        return

    # 从 api_settings.py → routes/ → web/ → src/ → 项目根目录
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
    if not os.path.exists(env_path):
        logger.warning(f".env 文件不存在: {env_path}")
        return

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    with open(env_path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.startswith("DEEPSEEK_MODEL="):
                f.write(f"DEEPSEEK_MODEL={model}\n")
                updated = True
            else:
                f.write(line)

    if updated:
        logger.info(f"✅ .env DEEPSEEK_MODEL 已更新为 {model}")
    else:
        logger.warning(f"⚠️ .env 中未找到 DEEPSEEK_MODEL= 行，未更新")


@router.get("")
async def get_settings():
    """获取当前配置（敏感字段脱敏）"""
    config = load_config()

    # AI 配置从数据库读取（脱敏）
    try:
        from ...database.db import get_all_ai_configs, get_active_ai_config
        ai_configs = get_all_ai_configs(mask_secrets=True)
        active_cfg = get_active_ai_config(mask_secrets=True)
        config["ai"] = {
            "active": active_cfg.get("config_key", "") if active_cfg else "",
            "configs": {c["config_key"]: c for c in ai_configs} if ai_configs else {},
        }
    except Exception as e:
        logger.warning(f"从数据库读取 AI 配置失败: {e}")

    if "site_7tan" in config:
        if "password" in config["site_7tan"]:
            config["site_7tan"]["password"] = "••••••••"

    if "oss" in config:
        if "access_key" in config["oss"]:
            config["oss"]["access_key"] = _mask_secret(str(config["oss"]["access_key"]))
        if "secret_key" in config["oss"]:
            config["oss"]["secret_key"] = "••••••••"

    return {"settings": config}


@router.put("")
async def update_settings(updates: dict):
    """更新配置"""
    try:
        config = load_config()

        # AI 配置单独处理：写入数据库
        ai_updates = updates.pop("ai", None)
        if ai_updates and "configs" in ai_updates:
            from ...database.db import save_ai_config, set_active_ai_config
            active_key = ai_updates.get("active", "")
            for key, cfg in ai_updates["configs"].items():
                if not isinstance(cfg, dict):
                    continue
                # 跳过脱敏的 api_key
                api_key = cfg.get("api_key", "")
                if "••••" in str(api_key):
                    api_key = ""  # 不覆盖已有 key
                is_active = 1 if key == active_key else 0
                save_ai_config(
                    config_key=key,
                    provider=cfg.get("provider", "deepseek"),
                    model=cfg.get("model", ""),
                    base_url=cfg.get("base_url", ""),
                    api_key=api_key,
                    context_window=cfg.get("context_window", 128000),
                    max_tokens=cfg.get("max_tokens", 16384),
                    temperature=cfg.get("temperature", 0.7),
                    is_active=is_active,
                )
            # 确保 active 正确
            if active_key:
                set_active_ai_config(active_key)
            logger.info(f"⚙️ AI 配置已写入数据库")

            # 🔄 同步 .env 中的模型变量
            if active_key:
                active_model = ai_updates["configs"].get(active_key, {}).get("model", "")
                _update_env_model(active_key, active_model)

        elif ai_updates and "active" in ai_updates:
            # 仅切换 active（无 configs 变更）→ 同步到 YAML
            config.setdefault("ai", {})["active"] = ai_updates["active"]
            logger.info(f"⚙️ AI active 已同步到 YAML: {ai_updates['active']}")

            # 🔄 同步 .env 中的模型变量（从数据库读取模型名）
            try:
                from ...database.db import get_active_ai_config
                active_cfg = get_active_ai_config(mask_secrets=False)
                if active_cfg:
                    _update_env_model(ai_updates["active"], active_cfg.get("model", ""))
            except Exception as e:
                logger.warning(f"同步 .env 模型变量失败: {e}")

        # 其余配置写入 YAML
        def deep_merge(base: dict, overlay: dict):
            for key, value in overlay.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    deep_merge(base[key], value)
                elif isinstance(value, str) and "••••" in value:
                    continue
                else:
                    base[key] = value

        deep_merge(config, updates)
        save_config(config)

        # 清除模型缓存
        try:
            from ...agent.model_manager import clear_model_cache
            clear_model_cache()
        except Exception:
            pass

        logger.info("⚙️ 配置已更新")
        return {"success": True, "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restart")
async def restart():
    """重启程序"""
    logger.info("🔄 收到重启请求")
    restart_self()
    return {"success": True, "message": "正在重启..."}


# ===== 调度器 API =====

@router.get("/scheduler")
async def get_scheduler_config():
    """获取定时采集配置"""
    config = load_config()
    sched_cfg = config.get("scheduler", {})
    cron_jobs = sched_cfg.get("cron_jobs", [])
    
    # 提取每日三次采集的时间
    times = {}
    for job in cron_jobs:
        name = job.get("name", "")
        cron = job.get("cron", "")
        # cron格式: "0 8 * * *" → 提取小时: "08:00"
        parts = cron.split()
        if len(parts) >= 2:
            times[name] = f"{parts[1].zfill(2)}:00"
    
    # 获取调度器状态
    from ...scheduler.scheduler import get_scheduler
    sched = get_scheduler()
    is_running = sched.running if sched else False
    
    # 获取下次运行时间
    next_jobs = []
    if is_running:
        for job in sched.get_jobs():
            next_jobs.append({
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })
    
    return {
        "enabled": sched_cfg.get("auto_publish", True),
        "is_running": is_running,
        "times": times,
        "next_jobs": next_jobs,
    }


@router.put("/scheduler")
async def update_scheduler_config(data: dict):
    """更新定时采集配置"""
    config = load_config()
    sched_cfg = config.setdefault("scheduler", {})
    
    # 更新启用状态
    if "enabled" in data:
        sched_cfg["auto_publish"] = bool(data["enabled"])
    
    # 更新采集时间（三个每日定时）
    if "times" in data and isinstance(data["times"], dict):
        cron_map = {
            "每日早间更新": "0 8 * * *",
            "每日午间更新": "0 12 * * *",
            "每日晚间更新": "0 18 * * *",
        }
        for name, time_str in data["times"].items():
            if name in cron_map and time_str:
                try:
                    hour = str(int(time_str.split(":")[0]))
                    cron_map[name] = f"0 {hour} * * *"
                except (ValueError, IndexError):
                    pass
        
        sched_cfg["cron_jobs"] = [
            {"name": name, "cron": cron, "task": name}
            for name, cron in cron_map.items()
        ]
    
    save_config(config)
    
    # 重启调度器以应用新配置
    try:
        from ...scheduler.scheduler import stop_scheduler, start_scheduler
        stop_scheduler()
        start_scheduler(config)
    except Exception as e:
        logger.warning(f"重启调度器失败: {e}")
    
    return {"success": True, "message": "定时采集配置已更新"}
