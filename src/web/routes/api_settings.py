"""
配置读写 API
GET  /api/settings         — 获取配置（脱敏）
PUT  /api/settings         — 更新配置
POST /api/settings/restart — 重启程序
"""
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
