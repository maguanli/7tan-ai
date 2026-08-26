"""
运行时遥测上报 — 完整版水印回传（P2 第③层）

- 仅完整版（BUILD_ID 以 PRO- 开头）上报，免费版（FREE）不上报
- 只上报：build_id / build_user / 构建时间 / 平台 / 时间戳（无隐私数据）
- 静默失败：网络异常、超时、配置缺失一律不影响软件启动与使用
- 节流：同一机器 24 小时内最多上报 1 次（记录于 data/telemetry_last.json）
"""
import json
import logging
import platform
import threading
import time
from pathlib import Path

_logger = logging.getLogger("telemetry")

# 默认上报端点（config.yaml 的 telemetry.endpoint 可覆盖）
DEFAULT_ENDPOINT = "https://www.7tan.com/api/telemetry/build.php"

REPORT_INTERVAL_HOURS = 24

try:
    from src.config.build_info import BUILD_ID, BUILD_TIME, BUILD_USER
except Exception:  # 极端情况：水印文件缺失
    BUILD_ID, BUILD_TIME, BUILD_USER = "FREE", "", ""


def _endpoint() -> str:
    """读取上报端点，config.yaml telemetry.enabled=false 时禁用。
    端点优先取加密容器（sec_config.pyd），防篡改 config.yaml 指向恶意服务器。"""
    try:
        from src.config.loader import load_config
        cfg = load_config() or {}
        tel = cfg.get("telemetry") or {}
        if tel.get("enabled", True) is False:
            return ""
    except Exception:
        pass
    try:
        from src.security.sec_config import get_telemetry_endpoint
        return get_telemetry_endpoint()
    except Exception:
        return DEFAULT_ENDPOINT


def _last_report_path() -> Path:
    try:
        from src.config.loader import ROOT_DIR
        return Path(ROOT_DIR) / "data" / "telemetry_last.json"
    except Exception:
        return Path("data/telemetry_last.json")


def _should_report() -> bool:
    """节流：24h 内不重复上报"""
    try:
        p = _last_report_path()
        if not p.exists():
            return True
        last = json.loads(p.read_text(encoding="utf-8")).get("ts", 0)
        return time.time() - last > REPORT_INTERVAL_HOURS * 3600
    except Exception:
        return True


def _report() -> None:
    if not BUILD_ID or BUILD_ID.startswith("FREE"):
        return  # 免费版不上报
    url = _endpoint()
    if not url:
        return
    if not _should_report():
        return
    payload = {
        "build_id": BUILD_ID,
        "build_user": BUILD_USER,
        "version": BUILD_TIME,
        "platform": platform.system(),
        "ts": int(time.time()),
    }
    try:
        from src.security.sec_config import get_pinned_session
        resp = get_pinned_session(url).post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        resp.raise_for_status()
        p = _last_report_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"ts": payload["ts"]}), encoding="utf-8")
        _logger.info("telemetry report OK: %s", BUILD_ID)
    except Exception as exc:
        # 静默失败，只记 debug 日志，绝不影响主流程
        _logger.debug("telemetry report skipped: %s", exc)


def report_async() -> None:
    """启动后异步上报（后台线程，不阻塞启动）"""
    try:
        threading.Thread(target=_report, daemon=True, name="telemetry").start()
    except Exception:
        pass
