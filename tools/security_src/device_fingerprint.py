"""
设备指纹 + 本地烙印记 + 服务器多设备检测（防转卖溯源）

功能:
  1. collect_fingerprint() — 采集设备指纹（主板/CPU/硬盘/MAC/MachineGuid → SHA256）
  2. stamp_owner()          — 登录后把用户名秘密烙进本地（多位置冗余）
  3. report_device()        — 登录后异步上报设备指纹到服务器（多设备检测）
  4. on_login()             — 登录成功后统一入口（幂等，节流防重复）

设计原则:
  - 全部静默失败，绝不影响登录与软件使用
  - 指纹为 SHA256 哈希（不可逆），不上报任何敏感原始信息
  - 烙印记为轻混淆（防小白删除），非加密机密
"""
import base64
import hashlib
import json
import logging
import os
import platform
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path

import requests

_logger = logging.getLogger("device_fp")

DEFAULT_API = "https://www.7tan.com/api/auth/device.php"
REPORT_THROTTLE_SECONDS = 3600  # 同一设备 1 小时内最多上报一次（登录多次也不刷屏）


def _data_dir() -> Path:
    try:
        from src.config.loader import ROOT_DIR
        return Path(ROOT_DIR) / "data"
    except Exception:
        return Path("data")


def _auth_dir() -> Path:
    d = _data_dir() / "auth"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


# ============================================================
# ① 设备指纹采集
# ============================================================

def _run_wmic(alias: str, field: str) -> str:
    """执行 wmic 查询，返回第一个非空值（Windows）"""
    if os.name != "nt":
        return ""
    try:
        r = subprocess.run(
            ["wmic", alias, "get", field],
            capture_output=True, text=True, timeout=6,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in (r.stdout or "").splitlines():
            v = line.strip()
            if v and v.lower() != field.lower():
                return v
    except Exception:
        pass
    return ""


def _machine_guid() -> str:
    """读取 Windows 注册表 MachineGuid（系统安装唯一标识）"""
    if os.name != "nt":
        return ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Cryptography") as k:
            v, _ = winreg.QueryValueEx(k, "MachineGuid")
            return str(v)
    except Exception:
        return ""


def collect_fingerprint() -> dict:
    """采集设备指纹，返回 {device_id, fingerprint, device_name, os_info}"""
    parts = [
        platform.node(),                        # 主机名
        platform.machine(),                     # 架构
        str(uuid.getnode()),                    # MAC 地址
        _machine_guid(),                        # 机器 GUID
        _run_wmic("baseboard", "serialnumber"),   # 主板序列号
        _run_wmic("csproduct", "uuid"),           # 计算机 UUID
        _run_wmic("cpu", "processorid"),          # CPU ID
        _run_wmic("diskdrive", "serialnumber"),   # 硬盘序列号
        _run_wmic("bios", "serialnumber"),        # BIOS 序列号
    ]
    raw = "|".join(parts)
    full = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()
    return {
        "device_id": full[:32],               # 短 ID（数据库唯一索引用）
        "fingerprint": full,                  # 完整指纹
        "device_name": socket.gethostname() or platform.node(),
        "os_info": f"{platform.system()} {platform.release()}",
    }


# ============================================================
# ② 本地烙印记（多位置冗余，转卖溯源用）
# ============================================================

def _owner_payload(username: str) -> str:
    """生成烙印内容（倒序+base64 轻混淆，防一眼看出明文）"""
    fp = collect_fingerprint()
    mark = json.dumps({
        "user": username,
        "ts": int(time.time()),
        "fp": fp["device_id"],
        "app": "7Tan",
    }, ensure_ascii=False)
    return base64.b64encode(mark.encode("utf-8")[::-1]).decode("ascii")


def _write_owner_file(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False


def _stamp_registry(content: str) -> bool:
    """写注册表 HKCU\\Software\\7Tan\\owner（删软件目录也不丢）"""
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\7Tan") as k:
            winreg.SetValueEx(k, "owner", 0, winreg.REG_SZ, content)
        return True
    except Exception:
        return False


def stamp_owner(username: str) -> bool:
    """登录后把用户名秘密烙进本地（3 处冗余）"""
    try:
        content = _owner_payload(username)
        ok = 0
        ok += _write_owner_file(_auth_dir() / "owner.dat", content)
        ok += _write_owner_file(Path(os.environ.get("APPDATA", "")) / "7Tan" / "owner.dat", content)
        ok += _stamp_registry(content)
        _logger.info("[DeviceFP] 烙印记写入完成 (%d/3): %s", ok, username)
        return ok > 0
    except Exception:
        _logger.debug("[DeviceFP] 烙印记写入失败（忽略）", exc_info=True)
        return False


def read_owner_mark() -> dict | None:
    """读取本地烙印（供管理/调试查询）"""
    candidates = [
        _auth_dir() / "owner.dat",
        Path(os.environ.get("APPDATA", "")) / "7Tan" / "owner.dat",
    ]
    for p in candidates:
        try:
            if p.exists():
                raw = base64.b64decode(p.read_text(encoding="utf-8").strip())
                return json.loads(raw[::-1].decode("utf-8"))
        except Exception:
            continue
    return None


# ============================================================
# ③ 上报设备指纹到服务器（多设备检测）
# ============================================================

def _throttle_ok() -> bool:
    """节流：1 小时内不重复上报"""
    try:
        p = _auth_dir() / "device_last_report.json"
        if p.exists():
            last = json.loads(p.read_text(encoding="utf-8")).get("ts", 0)
            if time.time() - last < REPORT_THROTTLE_SECONDS:
                return False
    except Exception:
        pass
    return True


def _api_url() -> str:
    try:
        from src.config.loader import load_config
        cfg = load_config() or {}
        base = (cfg.get("site_7tan", {}) or {}).get("base_url") or ""
        if base:
            return base.rstrip("/") + "/api/auth/device.php"
    except Exception:
        pass
    return DEFAULT_API


def report_device(token: str, username: str) -> dict | None:
    """上报设备指纹（同步执行，静默失败）。返回服务器 data 或 None。"""
    if not token:
        return None
    if not _throttle_ok():
        return None
    fp = collect_fingerprint()
    payload = {
        "token": token,
        "device_id": fp["device_id"],
        "fingerprint": fp["fingerprint"],
        "device_name": fp["device_name"],
        "os_info": fp["os_info"],
    }
    try:
        resp = requests.post(_api_url(), json=payload, timeout=6)
        data = {}
        try:
            data = resp.json()
        except Exception:
            pass
        # 记录节流时间（无论成败，避免频繁重试刷服务器）
        try:
            (_auth_dir() / "device_last_report.json").write_text(
                json.dumps({"ts": int(time.time())}), encoding="utf-8")
        except Exception:
            pass
        if resp.status_code == 200 and data.get("code") == 0:
            info = data.get("data", {})
            _logger.info("[DeviceFP] 设备上报成功: %s 设备数=%s 可疑=%s",
                         username, info.get("device_count"), info.get("suspicious"))
            return info
        _logger.debug("[DeviceFP] 上报返回异常: %s %s", resp.status_code, data.get("message"))
    except Exception as exc:
        _logger.debug("[DeviceFP] 上报失败（忽略）: %s", exc)
        try:
            (_auth_dir() / "device_last_report.json").write_text(
                json.dumps({"ts": int(time.time())}), encoding="utf-8")
        except Exception:
            pass
    return None


def on_login(user_info: dict) -> None:
    """登录成功后统一入口：本地烙印记 + 异步上报设备指纹（不阻塞 UI）"""
    try:
        username = user_info.get("username") or ""
        token = user_info.get("token") or ""
        if not username:
            return
        # ① 烙印记（同步，毫秒级）
        stamp_owner(username)
        # ② 上报（异步，静默）
        if token:
            threading.Thread(target=report_device, args=(token, username),
                             daemon=True, name="device-fp").start()
    except Exception:
        _logger.debug("[DeviceFP] on_login 异常（忽略）", exc_info=True)
