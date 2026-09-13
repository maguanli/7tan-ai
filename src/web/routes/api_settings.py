"""
配置读写 API
GET  /api/settings         — 获取配置（脱敏）
PUT  /api/settings         — 更新配置
POST /api/settings/restart — 重启程序
"""
import os

from fastapi import APIRouter, HTTPException, Request
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


def _update_env_vision(vision: dict):
    """同步 .env 中的视觉模型环境变量（VISION_API_KEY / VISION_BASE_URL / VISION_MODEL）"""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
    updates = {}
    for env_key, cfg_key in (("VISION_API_KEY", "api_key"), ("VISION_BASE_URL", "base_url"), ("VISION_MODEL", "model")):
        v = vision.get(cfg_key)
        if v and "••••" not in str(v) and "***" not in str(v):
            updates[env_key] = str(v).strip()
    if not updates:
        return
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    found = set()
    with open(env_path, "w", encoding="utf-8") as f:
        for line in lines:
            matched = False
            for env_key in updates:
                if line.startswith(env_key + "="):
                    f.write(f"{env_key}={updates[env_key]}\n")
                    found.add(env_key)
                    matched = True
                    break
            if not matched:
                f.write(line)
        for env_key, val in updates.items():
            if env_key not in found:
                f.write(f"{env_key}={val}\n")
    logger.info(f"✅ .env 视觉模型变量已更新: {list(updates.keys())}")


@router.get("")
async def get_settings():
    """获取当前配置（敏感字段脱敏）"""
    config = load_config()

    # AI 配置从数据库读取（脱敏）
    try:
        from ...database.db import get_all_ai_configs, get_active_ai_config
        ai_configs = get_all_ai_configs(mask_secrets=True)
        active_cfg = get_active_ai_config(mask_secrets=True)
        # 视觉模型配置优先从数据库读取（脱敏），回退 config.yaml
        vision_cfg = {}
        try:
            from ...database.db import get_vision_config
            db_vision = get_vision_config(mask_secrets=True)
            if db_vision:
                vision_cfg = db_vision
        except Exception as e:
            logger.warning(f"从数据库读取视觉AI配置失败: {e}")
        if not vision_cfg:
            vision_cfg = (config.get("ai") or {}).get("vision") or {}
        if vision_cfg.get("api_key"):
            vision_cfg = dict(vision_cfg)
            vision_cfg["api_key"] = _mask_secret(vision_cfg["api_key"])
        config["ai"] = {
            "active": active_cfg.get("config_key", "") if active_cfg else "",
            "configs": {c["config_key"]: c for c in ai_configs} if ai_configs else {},
            "vision": vision_cfg,
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
        if ai_updates:
            # 🗑️ 删除 AI 配置（前端删除操作 → 同步数据库，否则重启后配置会恢复）
            deleted_keys = ai_updates.get("deleted") or []
            if deleted_keys:
                from ...database.db import delete_ai_config, get_all_ai_configs, ensure_default_ai_config, set_active_ai_config, get_active_ai_config
                for k in deleted_keys:
                    try:
                        delete_ai_config(k)
                        logger.info(f"🗑️ 已删除 AI 配置: {k}")
                    except Exception as e:
                        logger.warning(f"删除 AI 配置 {k} 失败: {e}")
                remaining = get_all_ai_configs(mask_secrets=False) or []
                if not remaining:
                    ensure_default_ai_config()
                    remaining = get_all_ai_configs(mask_secrets=False) or []
                valid = {c["config_key"] for c in remaining}
                new_active = ai_updates.get("active", "") or ""
                if new_active not in valid:
                    new_active = remaining[0]["config_key"] if remaining else ""
                if new_active:
                    set_active_ai_config(new_active)
                    try:
                        active_cfg = get_active_ai_config(mask_secrets=False)
                        if active_cfg:
                            _update_env_model(new_active, active_cfg.get("model", ""))
                    except Exception as e:
                        logger.warning(f"同步 .env 模型变量失败: {e}")
                # 修正 active，避免后续 elif 分支把 active 设置成已删除的 key
                if ai_updates.get("active") not in valid:
                    ai_updates["active"] = new_active
                logger.info(f"🗑️ AI 配置删除完成: {deleted_keys} → 当前活跃: {new_active}")
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
                # 读取数据库现有值：前端未传的字段用现有值兜底，防止默认值覆盖
                from ...database.db import get_ai_config_by_key
                existing = get_ai_config_by_key(key, mask_secrets=True) or {}
                save_ai_config(
                    config_key=key,
                    provider=cfg.get("provider", existing.get("provider", "deepseek")),
                    model=cfg.get("model", existing.get("model", "")),
                    base_url=cfg.get("base_url", existing.get("base_url", "")),
                    api_key=api_key,
                    context_window=cfg.get("context_window", existing.get("context_window", 128000)),
                    max_tokens=cfg.get("max_tokens", existing.get("max_tokens", 16384)),
                    temperature=cfg.get("temperature", existing.get("temperature", 0.25)),
                    is_active=is_active,
                    extra_config=cfg.get("extra_config") if cfg.get("extra_config") is not None else existing.get("extra_config"),
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
            # 仅切换 active（无 configs 变更）→ 写入数据库
            from ...database.db import set_active_ai_config
            set_active_ai_config(ai_updates["active"])
            logger.info(f"⚙️ AI active 已写入数据库: {ai_updates['active']}")

            # 🔄 同步 .env 中的模型变量（从数据库读取模型名）
            try:
                from ...database.db import get_active_ai_config
                active_cfg = get_active_ai_config(mask_secrets=False)
                if active_cfg:
                    _update_env_model(ai_updates["active"], active_cfg.get("model", ""))
            except Exception as e:
                logger.warning(f"同步 .env 模型变量失败: {e}")

        # 👁️ 视觉AI模型配置：写入数据库（加密）+ 同步 .env（VISION_*）+ 同步 config.yaml（ai.vision）
        vision_updates = (ai_updates or {}).get("vision")
        if isinstance(vision_updates, dict) and vision_updates:
            from ...database.db import get_vision_config, save_vision_config
            existing = get_vision_config(mask_secrets=False) or {}
            api_key = str(vision_updates.get("api_key", "") or "").strip()
            if not api_key or "••" in api_key or "***" in api_key:
                api_key = existing.get("api_key", "")
            base_url = str(vision_updates.get("base_url", "") or "").strip() or existing.get("base_url", "") or "https://open.bigmodel.cn/api/paas/v4"
            model = str(vision_updates.get("model", "") or "").strip() or existing.get("model", "") or "glm-4v-flash"
            save_vision_config(api_key=api_key, base_url=base_url, model=model)
            vision_cfg = {"api_key": api_key, "base_url": base_url, "model": model}
            config.setdefault("ai", {})["vision"] = vision_cfg
            _update_env_vision(vision_cfg)
            logger.info("👁️ 视觉AI模型配置已写入数据库")

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


@router.get("/ai/key/reveal")
async def reveal_ai_key(config_key: str):
    """查看指定 AI 配置的明文 API Key（本地管理后台，管理员自用）"""
    from ...database.db import get_ai_config_by_key
    cfg = get_ai_config_by_key(config_key, mask_secrets=False)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"AI 配置不存在: {config_key}")
    return {"config_key": config_key, "api_key": cfg.get("api_key", "")}


@router.get("/ai/vision-key/reveal")
async def reveal_vision_key():
    """查看视觉模型的明文 API Key（本地管理后台，管理员自用）"""
    from ...database.db import get_vision_config
    cfg = get_vision_config(mask_secrets=False)
    return {"api_key": (cfg or {}).get("api_key", "")}


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


# ============================================================
# 以下端点对应桌面版「设置」页的 Tab（插件市场/能力清单/环境引擎/记忆/提示词/关于）
# ============================================================

@router.get("/plugins")
async def get_plugins_settings():
    """插件市场：可用插件清单 + 安装状态"""
    try:
        from ...plugins.manager import get_manager
        mgr = get_manager()
        manifest = mgr.get_manifest() or []
        installed = set(mgr.get_installed() or [])
        plugins = []
        for p in manifest:
            pid = p.get("id", "")
            plugins.append({
                "id": pid,
                "name": p.get("name", pid),
                "version": p.get("version", ""),
                "author": p.get("author", ""),
                "category": p.get("category", ""),
                "description": p.get("description", ""),
                "tools": p.get("tools", []),
                "icon": p.get("icon", "🧩"),
                "installed": pid in installed,
            })
        return {"plugins": plugins, "installed_count": len(installed), "total": len(plugins)}
    except Exception as e:
        logger.warning(f"获取插件清单失败: {e}")
        return {"plugins": [], "installed_count": 0, "total": 0, "error": str(e)}


@router.post("/plugins/{plugin_id}/install")
async def install_plugin_api(plugin_id: str):
    """安装插件"""
    try:
        from ...plugins.manager import get_manager
        get_manager().install(plugin_id)
        return {"ok": True, "message": f"插件 {plugin_id} 安装成功（重启后生效）"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"安装失败: {e}")


@router.post("/plugins/{plugin_id}/uninstall")
async def uninstall_plugin_api(plugin_id: str):
    """卸载插件"""
    try:
        from ...plugins.manager import get_manager
        get_manager().uninstall(plugin_id)
        return {"ok": True, "message": f"插件 {plugin_id} 已卸载（重启后生效）"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"卸载失败: {e}")


@router.get("/capabilities")
async def get_capabilities_api():
    """能力清单：按类别分组的 AI 能力 + 统计摘要"""
    try:
        from ...database.db import get_capabilities_grouped
        groups = get_capabilities_grouped() or []
        total = local = cloud = 0
        for g in groups:
            for it in g.get("items", []):
                total += 1
                tool = str(it.get("tool", ""))
                if "本地" in tool or "(" in tool:
                    local += 1
                else:
                    cloud += 1
        return {"groups": groups, "stats": {"categories": len(groups), "total": total, "local": local, "cloud": cloud}}
    except Exception as e:
        logger.warning(f"获取能力清单失败: {e}")
        return {"groups": [], "stats": {"categories": 0, "total": 0, "local": 0, "cloud": 0}, "error": str(e)}


@router.get("/software")
async def get_software_api():
    """环境引擎：已安装软件/引擎清单"""
    try:
        from ...database.db import get_all_installed_software
        return {"software": get_all_installed_software() or []}
    except Exception as e:
        logger.warning(f"获取软件清单失败: {e}")
        return {"software": [], "error": str(e)}


@router.post("/software/scan")
async def scan_software_api():
    """环境引擎：重新扫描已安装软件"""
    try:
        from ...database.db import scan_and_sync_installed_software
        data = scan_and_sync_installed_software()
        if isinstance(data, dict) and data.get("error"):
            raise HTTPException(status_code=500, detail=data["error"])
        return {"ok": True, "message": "扫描完成", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描失败: {e}")


@router.get("/memories")
async def get_memories_api(section: str = "", keyword: str = ""):
    """记忆系统：列出记忆（可按分区/关键词过滤）"""
    try:
        from ...database.db import get_all_memories
        mems = get_all_memories(section=section or None, keyword=keyword or None, limit=500) or []
        return {"memories": mems, "total": len(mems)}
    except Exception as e:
        logger.warning(f"获取记忆列表失败: {e}")
        return {"memories": [], "total": 0, "error": str(e)}


@router.delete("/memories")
async def delete_memory_api(section: str, key: str):
    """记忆系统：删除一条记忆"""
    try:
        from ...database.db import delete_memory
        ok = delete_memory(section=section, key=key)
        if not ok:
            raise HTTPException(status_code=404, detail=f"未找到记忆 {section}/{key}")
        return {"ok": True, "message": f"已删除记忆 {section}/{key}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


@router.get("/prompt")
async def get_prompt_api(prompt_type: str = "system"):
    """系统提示词：读取指定类型的提示词（只读）"""
    try:
        from ...database.db import get_prompt_from_db
        p = get_prompt_from_db(prompt_type)
        if not p:
            # 回退：读取 data/prompts/{type}.txt
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            fp = os.path.join(base, "data", "prompts", f"{prompt_type}.txt")
            content = ""
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
            p = {"prompt_type": prompt_type, "content": content, "char_count": len(content),
                 "line_count": content.count("\n") + 1 if content else 0}
        return {"prompt": p}
    except Exception as e:
        logger.warning(f"获取提示词失败: {e}")
        return {"prompt": None, "error": str(e)}


@router.get("/about")
async def get_about_api():
    """关于 7Tan：版本 / 构建 / 路径信息"""
    info = {}
    try:
        from ...config.version import APP_VERSION
        info["version"] = APP_VERSION
    except Exception:
        info["version"] = "未知"
    try:
        from ...config.build_info import BUILD_ID
        info["build_id"] = BUILD_ID
    except Exception:
        info["build_id"] = ""
    try:
        from ...plugins.manager import PLUGIN_DIR
        info["plugin_dir"] = str(PLUGIN_DIR)
    except Exception:
        info["plugin_dir"] = ""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    info["project_root"] = base
    info["log_dir"] = os.path.join(base, "logs")
    info["data_dir"] = os.path.join(base, "data")
    try:
        from ...config.loader import load_config
        cfg = load_config()
        info["site_root"] = (cfg.get("site_7tan") or {}).get("base_url", "").replace("/api", "") or "https://www.7tan.com"
    except Exception:
        info["site_root"] = "https://www.7tan.com"
    return {"info": info}


# ===== 远程访问设置（WEB 版：局域网 / Token / 外网穿透）=====
@router.get("/remote")
async def get_remote_access(request: Request):
    """获取远程访问信息：局域网IP、端口、allow_lan、Token、穿透工具状态"""
    import socket as _socket

    # 1) 本机局域网 IP（UDP 探测 + 主机名解析）
    lan_ips = []
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip and ip not in lan_ips:
            lan_ips.append(ip)
        s.close()
    except Exception:
        pass
    try:
        for info in _socket.getaddrinfo(_socket.gethostname(), None, _socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in lan_ips:
                lan_ips.append(ip)
    except Exception:
        pass

    # 2) 端口：优先当前请求实际端口，兜底配置
    port = request.url.port
    if not port:
        try:
            port = (load_config().get("web") or {}).get("port") or 9800
        except Exception:
            port = 9800

    # 3) 配置项
    cfg = load_config()
    allow_lan = bool((cfg.get("web") or {}).get("allow_lan", False))
    host = (cfg.get("web") or {}).get("host", "0.0.0.0")

    # 4) Token
    token = _read_remote_token()

    # 5) 内网穿透工具进程检测
    tunnel_tools = _detect_tunnel_tools()

    return {
        "lan_ips": lan_ips,
        "port": port,
        "host": host,
        "allow_lan": allow_lan,
        "token": token,
        "token_masked": _mask_secret(token) if token else "",
        "tunnel_tools": tunnel_tools,
    }


def _read_remote_token() -> str:
    """读取当前生效的 API Token（环境变量 > data/.api_token）"""
    env_token = os.environ.get("7TAN_API_TOKEN", "").strip()
    if env_token:
        return env_token
    token_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", ".api_token")
    try:
        if os.path.exists(token_file):
            with open(token_file, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def _detect_tunnel_tools() -> list:
    """检测常见内网穿透/组网工具是否在运行（Windows tasklist）"""
    tools = ["frpc", "frps", "cpolar", "ngrok", "cloudflared", "zerotier", "tailscale"]
    found = []
    try:
        import subprocess
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        ).stdout.lower()
        for t in tools:
            if t in out:
                found.append(t)
    except Exception:
        pass
    return found


@router.put("/remote")
async def update_remote_access(body: dict):
    """更新远程访问配置（allow_lan 开关），保存后需重启服务生效"""
    config = load_config()
    web = config.setdefault("web", {})
    if "allow_lan" in body:
        web["allow_lan"] = bool(body["allow_lan"])
    save_config(config)
    logger.info(f"🌐 远程访问配置已保存: allow_lan={web.get('allow_lan')}（重启服务后生效）")
    return {"ok": True, "msg": "已保存，重启服务后生效"}


@router.post("/remote/regenerate-token")
async def regenerate_remote_token():
    """重新生成 API Token 并写入 data/.api_token，重启服务后生效"""
    import secrets
    token = secrets.token_urlsafe(32)
    token_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", ".api_token")
    try:
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception as e:
        logger.warning(f"API Token 写入失败: {e}")
        return {"ok": False, "msg": f"写入失败: {e}"}
    logger.info("🔑 API Token 已重新生成（重启服务后生效）")
    return {"ok": True, "token": token, "msg": "已重新生成，重启服务后生效"}
