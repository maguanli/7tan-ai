"""
按用户存储的偏好设置（新手引导状态等）

背景：旧版把 onboarding_completed / wizard_disabled 存在全局 config.yaml，
导致「一个用户看完引导，其他用户登录也不显示」。本模块改为每个用户独立存储：
  data/users/<sha1(username)>.json

兼容迁移：读取时若该用户无记录且全局 config 存在旧键，则一次性迁移给当前用户
并清除全局键（避免旧配置影响所有新用户）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from loguru import logger


def _root_dir() -> Path:
    """获取项目根目录 — 兼容开发模式和 PyInstaller 打包"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def _users_dir() -> Path:
    d = _root_dir() / "data" / "users"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def _user_file(username: str) -> Path:
    """用户名 → 安全文件名（sha1 摘要，避免特殊字符/路径穿越）"""
    name = (username or "default").strip() or "default"
    safe = hashlib.sha256(name.encode("utf-8")).hexdigest()[:24]
    return _users_dir() / f"{safe}.json"


def _load(username: str) -> dict:
    f = _user_file(username)
    try:
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"[UserPrefs] 读取用户配置失败 {f}: {e}")
    return {}


def _save(username: str, data: dict) -> None:
    try:
        _user_file(username).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"[UserPrefs] 保存用户配置失败: {e}")


def get_user_pref(username: str, key: str, default=False):
    """按用户读取偏好；无记录时尝试从旧全局 config 一次性迁移。"""
    data = _load(username)
    if key not in data:
        _migrate_legacy(username, key)
        data = _load(username)
    return data.get(key, default)


def set_user_pref(username: str, key: str, value) -> None:
    """按用户写入偏好。"""
    data = _load(username)
    data[key] = value
    _save(username, data)


def _migrate_legacy(username: str, key: str) -> None:
    """旧版把引导状态存在全局 config.yaml，迁移策略：

    - wizard_disabled（不再提示）：机器主人偏好，不迁移给任何用户，直接清除全局键。
      否则新用户登录会继承旧值而看不到引导。
    - onboarding_completed（已完成引导）：迁移给当前登录用户，避免主人重复看到引导遮罩。
    """
    try:
        from ..config.loader import load_config, save_config

        config = load_config()
        app_cfg = config.get("app", {})
        if key not in app_cfg:
            return
        val = app_cfg[key]
        if key == "wizard_disabled":
            # 不再提示：不迁移，直接清除（新用户默认显示引导）
            app_cfg.pop(key, None)
            save_config(config)
            logger.info("[UserPrefs] 已清除旧全局 wizard_disabled（不迁移，所有用户默认显示引导）")
        else:
            set_user_pref(username, key, val)
            app_cfg.pop(key, None)
            save_config(config)
            logger.info(f"[UserPrefs] 已迁移旧全局配置 {key}={val} → 用户 {username!r}")
    except Exception as e:
        logger.debug(f"[UserPrefs] 迁移跳过: {e}")
