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

    # 脱敏 AI 配置中的 api_key
    ai = config.get("ai", {})
    if "configs" in ai:
        for key, cfg in ai["configs"].items():
            if "api_key" in cfg and cfg["api_key"] and len(str(cfg["api_key"])) > 6:
                cfg["api_key"] = _mask_secret(str(cfg["api_key"]))
    elif "api_key" in ai:
        # 兼容旧格式
        ai["api_key"] = _mask_secret(str(ai["api_key"]))

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

        # 深度合并（跳过被脱敏的字段）
        def deep_merge(base: dict, overlay: dict):
            for key, value in overlay.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    deep_merge(base[key], value)
                elif isinstance(value, str) and "••••" in value:
                    # 脱敏值不覆盖真实值
                    continue
                else:
                    base[key] = value

        deep_merge(config, updates)
        save_config(config)

        # 清除模型缓存，下次请求使用新配置
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
