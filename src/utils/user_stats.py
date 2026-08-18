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

多次上报增强 (2026-08-02):
  - 启动时上报（force=True，必发）
  - 主界面打开/关闭时上报（force=False，进程内 60 秒节流，避免频繁刷新）
  - 关闭前上报使用短超时(3s) + 最多等待 1 秒，绝不阻塞程序退出
  → 使 DAU/最后活跃时间更贴近真实使用，跨天使用也能正确计入当天活跃
"""
import time
import threading
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

# ── 当前版本（与 src/config/version.py 保持一致，避免硬编码不同步）──
try:
    from ..config.version import APP_VERSION
    _APP_VERSION = APP_VERSION
except Exception:
    _APP_VERSION = "1.0.0"
APP_VERSION = _APP_VERSION

# ── 事件上报节流（秒）：主界面打开/关闭等事件，距上次事件上报不足此间隔则跳过 ──
PING_MIN_INTERVAL = 60.0

# 进程内状态（列表以便闭包修改）
_PING_LOCK = threading.Lock()
_last_event_ping_ts = [0.0]


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


def _try_ping(url: str, analytics_id: str, username: str, timeout: float = 10.0) -> bool:
    """向单个 URL 发送 ping，返回是否成功。"""
    ping_url = f"{url}?id={analytics_id}&ver={APP_VERSION}"
    if username:
        ping_url += f"&user={username}"

    try:
        with httpx.Client(timeout=timeout) as client:
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


def _check_event_throttle() -> bool:
    """事件上报节流：距上次事件上报不足 PING_MIN_INTERVAL 秒则跳过。

    启动上报（force=True）也会刷新节流时间戳，避免启动后立即关闭重复上报。
    """
    now = time.time()
    with _PING_LOCK:
        if now - _last_event_ping_ts[0] < PING_MIN_INTERVAL:
            return False
        _last_event_ping_ts[0] = now
    return True


def ping_analytics(timeout: float = 10.0, force: bool = True) -> bool:
    """
    发送统计 ping（A+B 方案：独立配置 + 主备 fallback）。

    Args:
        timeout: 单个请求超时秒数（关闭前上报建议 3.0，避免拖慢退出）
        force:   True=总是发送（启动时）；False=遵循 60 秒节流（界面打开/关闭事件）

    依次尝试 primary → fallback，任一成功即停止。

    上报内容:
      - id:   匿名设备 GUID（16位 hex）
      - ver:  客户端版本号
      - user: 用户名（可选，用于关联）

    Returns:
        True 如果至少一个端点上报成功；被节流跳过时返回 False
    """
    if not force and not _check_event_throttle():
        logger.debug("[UserStats] 事件上报被节流跳过（60s 内已上报过）")
        return False

    analytics_id = _get_or_create_analytics_id()
    username = _get_username()
    urls = _get_ping_urls()

    for i, url in enumerate(urls):
        label = "主" if i == 0 else "备"
        if _try_ping(url, analytics_id, username, timeout=timeout):
            logger.info(f"[UserStats] ✅ {label}端点 ping 成功 (id={analytics_id[:8]}...)")
            return True
        else:
            logger.debug(f"[UserStats] ⚠️ {label}端点 ping 失败: {url}")

    logger.warning("[UserStats] ❌ 所有端点 ping 均失败（网络不可达或服务端未部署）")
    return False


def ping_analytics_async(force: bool = True):
    """异步发送统计 ping（不阻塞 UI）。

    Args:
        force: True=总是发送（默认，兼容旧调用）；False=遵循节流
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_async_ping(force))
        else:
            ping_analytics(force=force)
    except RuntimeError:
        # 没有事件循环，同步发送
        ping_analytics(force=force)


def ping_on_close():
    """
    主窗口关闭前上报（短超时，最多等待 1 秒，绝不阻塞程序退出）。

    使 DAU 统计更贴近真实：用户跨天使用（昨天启动、今天才关闭）时，
    关闭瞬间的上报能把"今天活跃"正确记上。
    """
    def _do():
        try:
            ping_analytics(timeout=3.0, force=False)
        except Exception:
            pass

    try:
        t = threading.Thread(target=_do, daemon=True, name="stats-ping-close")
        t.start()
        t.join(1.0)  # 最多等 1 秒，超时直接放行退出
    except Exception:
        pass


async def _async_ping(force: bool = True):
    """异步执行 ping。"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: ping_analytics(force=force))
    except Exception:
        pass
