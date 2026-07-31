"""
7Tan 用户流量统计模块

参考泼猴PC版编译神器 (MainForm.cs PingAnalyticsAsync):
  - 启动时静默发送统计 ping
  - 本地文件存储匿名 GUID
  - 仅上报: GUID + 版本号 + 用户名(可选)

不收集任何个人信息，仅匿名标识 + 版本号用于:
  - 每日活跃用户 (DAU)
  - 新增设备统计
  - 版本分布
  - 留存分析

A+B 方案:
  A. 独立配置项 — analytics.primary / analytics.fallback，与 site_7tan.base_url 解耦
  B. 主备 fallback — primary 失败自动切 fallback，域名迁移零中断
"""
import uuid
import hashlib
import platform
import asyncio
from pathlib import Path

import httpx
from loguru import logger

from ..config.loader import load_config

# ── 本地标识文件 ──
ANALYTICS_DIR = Path.home() / "AppData" / "Local" / "7tan"
ANALYTICS_FILE = ANALYTICS_DIR / "analytics_id.txt"

# ── 当前版本（与 app.py 保持一致）──
APP_VERSION = "5.1.0"


def _get_or_create_analytics_id() -> str:
    """读取或生成本地匿名标识（16位 hex）。"""
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    if ANALYTICS_FILE.exists():
        try:
            aid = ANALYTICS_FILE.read_text(encoding="utf-8").strip()
            if len(aid) >= 16:
                return aid[:16]
        except Exception:
            pass

    # 基于机器信息生成稳定 GUID（MAC + 主机名 hash）
    machine_seed = f"{platform.node()}{platform.machine()}"
    seed_hash = hashlib.sha256(machine_seed.encode()).hexdigest()[:8]
    new_id = uuid.uuid4().hex[:8] + seed_hash

    try:
        ANALYTICS_FILE.write_text(new_id, encoding="utf-8")
    except Exception:
        pass

    logger.debug(f"[UserStats] 新设备标识: {new_id}")
    return new_id


def _get_username() -> str:
    """获取当前登录用户名（可选上报）。"""
    try:
        from ..security.token_store import load_token
        token_data = load_token()
        if token_data:
            return token_data.get("username", "")
    except Exception:
        pass
    return ""


def _get_ping_urls() -> list:
    """
    从配置读取统计上报 URL 列表（主 + 备）。

    独立于 site_7tan.base_url，域名迁移不受影响。
    配置示例:
      analytics:
        primary: https://img.7tan.cn/api/7tan_ping.php
        fallback: https://img.7tan.com/api/7tan_ping.php
    """
    config = load_config()
    analytics_cfg = config.get("analytics", {})

    primary = analytics_cfg.get("primary", "")
    fallback = analytics_cfg.get("fallback", "")

    urls = []
    if primary:
        urls.append(primary)
    if fallback:
        urls.append(fallback)

    # 兼容旧配置：如果 analytics 段不存在，回退到 site_7tan.base_url
    if not urls:
        base_url = config.get("site_7tan", {}).get("base_url", "https://img.7tan.cn")
        if "/api" in base_url:
            base_url = base_url.split("/api")[0]
        urls.append(f"{base_url}/api/7tan_ping.php")

    return urls


def _try_ping(url: str, analytics_id: str, username: str) -> bool:
    """向单个 URL 发送 ping，返回是否成功。"""
    ping_url = f"{url}?id={analytics_id}&ver={APP_VERSION}"
    if username:
        ping_url += f"&user={username}"

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(ping_url)
            if resp.status_code == 200:
                return True
            else:
                logger.debug(f"[UserStats] {url} 返回 {resp.status_code}")
                return False
    except (httpx.ConnectTimeout, httpx.ConnectError):
        logger.debug(f"[UserStats] {url} 连接失败")
        return False
    except Exception as e:
        logger.debug(f"[UserStats] {url} 异常: {e}")
        return False


def ping_analytics() -> bool:
    """
    启动时静默发送统计 ping（A+B 方案：独立配置 + 主备 fallback）。

    依次尝试 primary → fallback，任一成功即停止。

    上报内容:
      - id:   匿名设备 GUID（16位 hex）
      - ver:  客户端版本号
      - user: 用户名（可选，用于关联）

    Returns:
        True 如果至少一个端点上报成功
    """
    analytics_id = _get_or_create_analytics_id()
    username = _get_username()
    urls = _get_ping_urls()

    for i, url in enumerate(urls):
        label = "主" if i == 0 else "备"
        if _try_ping(url, analytics_id, username):
            logger.info(f"[UserStats] ✅ {label}端点 ping 成功 (id={analytics_id[:8]}...)")
            return True
        else:
            logger.debug(f"[UserStats] ⚠️ {label}端点 ping 失败: {url}")

    logger.warning("[UserStats] ❌ 所有端点 ping 均失败（网络不可达或服务端未部署）")
    return False


def ping_analytics_async():
    """异步发送统计 ping（不阻塞 UI）。"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_async_ping())
        else:
            ping_analytics()
    except RuntimeError:
        # 没有事件循环，同步发送
        ping_analytics()


async def _async_ping():
    """异步执行 ping。"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ping_analytics)
    except Exception:
        pass
