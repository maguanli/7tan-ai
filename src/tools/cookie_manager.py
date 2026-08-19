"""浏览器 Cookie 持久化：导出/恢复/自动保存，重启保持登录态

问题根因：
    PyInstaller onefile 打包下，QWebEngineProfile 默认持久化路径会随解压临时
    目录漂移（或落入沙箱临时区），导致 Cookies 数据库从未真正落盘，
    软件一重启登录态就丢失。

方案（双保险）：
    1. ensure_profile_storage():
       显式把 persistentStoragePath / cachePath 固定到项目 data/browser_profile，
       QtWebEngine 的 Cookies 数据库、Local Storage 全部落盘，重启自动恢复。
    2. export/restore:
       监听 cookieStore.cookiesAdded/Removed，防抖导出全部 Cookie（含 HttpOnly）
       到 data/browser_cookies.json；启动时批量注入恢复。
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QByteArray, QTimer
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWebEngineCore import QWebEngineProfile

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE_DIR = ROOT / "data" / "browser_profile"          # QtWebEngine 固定存储目录
COOKIE_FILE = ROOT / "data" / "browser_cookies.json"     # 兜底导出文件
COOKIE_FILE_BAK = ROOT / "data" / "browser_cookies.json.bak"

_SAVE_DEBOUNCE_MS = 1500                                  # Cookie 变化防抖保存间隔
_save_timer: QTimer | None = None
_saving = False


def _get_profile() -> QWebEngineProfile:
    """默认 profile（所有内置浏览器窗口共享）"""
    return QWebEngineProfile.defaultProfile()


def ensure_profile_storage() -> None:
    """把 QtWebEngine 持久化存储固定到本地目录（重启不丢 Cookie/LocalStorage）"""
    try:
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        profile = _get_profile()
        profile.setPersistentStoragePath(str(PROFILE_DIR))
        profile.setCachePath(str(PROFILE_DIR / "cache"))
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        logger.info(f"🌐 浏览器持久化存储已固定: {PROFILE_DIR}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"浏览器持久化存储设置失败: {e}")


def _export_to_file(cookies: list) -> int:
    """把 QNetworkCookie 列表写入 JSON（原子写入 + 备份）"""
    global _saving
    if _saving:
        return 0
    _saving = True
    try:
        raw_list = []
        for c in cookies:
            try:
                raw = c.toRawForm().data()  # bytes（含 name/value/domain/path/secure/HttpOnly）
                if raw:
                    raw_list.append(base64.b64encode(raw).decode("ascii"))
            except Exception:  # noqa: BLE001
                continue
        if not raw_list:
            return 0
        payload = {
            "version": 1,
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(raw_list),
            "cookies": raw_list,
        }
        tmp = COOKIE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        if COOKIE_FILE.exists():
            try:
                COOKIE_FILE.replace(COOKIE_FILE_BAK)
            except Exception:  # noqa: BLE001
                pass
        tmp.replace(COOKIE_FILE)
        logger.info(f"🍪 Cookie 已导出 {len(raw_list)} 条 → {COOKIE_FILE.name}")
        return len(raw_list)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Cookie 导出失败: {e}")
        return 0
    finally:
        _saving = False


def export_cookies() -> int:
    """主动导出当前全部 Cookie（含 HttpOnly）。

    QtWebEngine 的 loadAllCookies 是异步的：先触发 cookiesAdded 信号，
    稍后统一收集写入文件。返回本次收集条数。
    """
    try:
        store = _get_profile().cookieStore()
        collected: list = []

        def _on_added(cookie_list):
            collected.extend(cookie_list)

        store.cookiesAdded.connect(_on_added)
        try:
            store.loadAllCookies()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"loadAllCookies 失败: {e}")

        def _flush():
            try:
                store.cookiesAdded.disconnect(_on_added)
            except Exception:  # noqa: BLE001
                pass
            _export_to_file(collected)

        QTimer.singleShot(2000, _flush)
        return len(collected)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"导出 Cookie 异常: {e}")
        return 0


def restore_cookies() -> int:
    """启动时从 JSON 恢复全部 Cookie（在创建任何 QWebEngineView 之前调用）"""
    if not COOKIE_FILE.exists():
        return 0
    try:
        data = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
        raw_list = data.get("cookies", [])
        store = _get_profile().cookieStore()
        ok = 0
        for b64 in raw_list:
            try:
                raw = base64.b64decode(b64)
                for c in QNetworkCookie.parseCookies(QByteArray(raw)):
                    store.setCookie(c)
                    ok += 1
            except Exception:  # noqa: BLE001
                continue
        logger.info(f"🍪 已恢复 {ok} 条 Cookie（来源 {COOKIE_FILE.name}）")
        return ok
    except Exception as e:  # noqa: BLE001
        logger.warning(f"恢复 Cookie 失败: {e}")
        return 0


def _schedule_save() -> None:
    """防抖：Cookie 变化后延迟统一保存，避免频繁写盘"""
    global _save_timer
    if _save_timer is not None:
        _save_timer.stop()
    else:
        _save_timer = QTimer()
        _save_timer.setSingleShot(True)
        _save_timer.timeout.connect(export_cookies)
    _save_timer.start(_SAVE_DEBOUNCE_MS)


def setup_cookie_persistence() -> None:
    """应用启动时调用一次（QApplication 创建后、任何浏览器窗口创建前）：
    1. 固定持久化存储路径  2. 恢复已保存 Cookie  3. 监听变化自动导出
    """
    ensure_profile_storage()
    restore_cookies()
    try:
        store = _get_profile().cookieStore()
        store.cookiesAdded.connect(lambda _c: _schedule_save())
        store.cookiesRemoved.connect(lambda _c: _schedule_save())
        logger.info("🍪 Cookie 自动导出监听已开启")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Cookie 监听绑定失败: {e}")
