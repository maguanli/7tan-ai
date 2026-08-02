"""
软件更新系统 — 检查 / 下载 / 校验 / 应用

服务器清单: https://www.7tan.com/api/update/check.php（读 updates/version.json）
更新包:     https://www.7tan.com/updates/7tan-editor-free-vX.Y.Z.zip

流程:
  1. check_for_update()  → GET 服务器, 比对版本, 返回最新版本信息或 None
  2. download_update()   → 下载 zip → MD5 校验 → 返回本地路径
  3. apply_update()      → 解压 + 生成 update.bat → 启动 → 主程序退出 → bat 覆盖并重启

开发模式（非 frozen / python 源码运行）不支持自更新，仅提示用 git pull。
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests
from loguru import logger

try:
    from src.config.version import APP_NAME, APP_VERSION
except Exception:  # 极端情况：版本文件缺失
    APP_NAME, APP_VERSION = "7tan-editor", "0.0.0"

DEFAULT_ENDPOINT = "https://www.7tan.com/api/update/check.php"
DEFAULT_BASE = "https://www.7tan.com/updates"
UPDATE_DIR_NAME = "_update"
DOWNLOAD_TIMEOUT = (30, 300)  # (连接, 读取) 秒


def _cfg() -> dict:
    """读取 config.yaml 的 update 配置节"""
    try:
        from src.config.loader import load_config
        cfg = load_config() or {}
        return cfg.get("update") or {}
    except Exception:
        return {}


def endpoint() -> str:
    # 优先使用加密容器中的端点（防篡改 config.yaml 指向恶意服务器）
    try:
        from src.security.sec_config import get_update_endpoint
        return get_update_endpoint()
    except Exception:
        pass
    return _cfg().get("endpoint") or DEFAULT_ENDPOINT


def channel() -> str:
    return _cfg().get("channel") or "stable"


def is_enabled() -> bool:
    return _cfg().get("enabled", True) is not False


def auto_check_enabled() -> bool:
    return _cfg().get("auto_check", True) is not False


def compare_versions(a: str, b: str) -> int:
    """语义化版本比较 a vs b → -1(a<b) / 0 / 1(a>b)"""
    def norm(v: str) -> list:
        parts = []
        for p in str(v).strip().lstrip("vV").replace("-", ".").split("."):
            parts.append(int(p) if p.isdigit() else 0)
        while len(parts) < 3:
            parts.append(0)
        return parts[:3]

    na, nb = norm(a), norm(b)
    return -1 if na < nb else (1 if na > nb else 0)


def _platform_tag() -> str:
    """平台标识归一化: win32/win64 → windows"""
    p = sys.platform.lower()
    if p.startswith("win"):
        return "windows"
    if p.startswith("linux"):
        return "linux"
    if p.startswith("darwin"):
        return "macos"
    return p


def check_for_update(timeout: int = 10) -> dict | None:
    """
    检查更新。
    返回:
      - None                        → 无更新 / 已是最新
      - {"error": "..."}            → 检查失败（网络等）
      - latest 信息 dict            → 有更新（含 version/url/md5/size/notes）
    """
    if not is_enabled():
        return None
    try:
        from src.security.sec_config import get_pinned_session
        resp = get_pinned_session(endpoint()).get(
            endpoint(),
            params={"ver": APP_VERSION, "platform": _platform_tag(), "channel": channel()},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug(f"update check failed: {exc}")
        return {"error": f"无法连接更新服务器: {exc}"}

    latest = data.get("latest")
    if not latest or not data.get("has_update"):
        return None
    if compare_versions(latest.get("version", "0"), APP_VERSION) <= 0:
        return None
    return latest


def _update_dir() -> Path:
    """更新临时目录 = exe 同级目录/_update"""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    return base / UPDATE_DIR_NAME


def _verify_rsa_signature(url: str, zip_path: Path) -> bool:
    """
    下载 <url>.sig 并验证 zip 的 RSA 签名（SHA-256 + PKCS1v15）。
    使用内置公钥（与服务器 JWT 私钥配对），验签失败返回 False。
    """
    try:
        sig_url = url + ".sig"
        from src.security.sec_config import get_pinned_session
        resp = get_pinned_session(sig_url).get(sig_url, timeout=DOWNLOAD_TIMEOUT)
        if resp.status_code != 200:
            logger.warning(f"signature file not available: {sig_url} (HTTP {resp.status_code})")
            return False
        sig_b64 = resp.text.strip()
        if not sig_b64:
            return False

        import hashlib
        h = hashlib.sha256()
        with open(zip_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)

        from src.security.sec_config import verify_update_signature_with_hash
        return verify_update_signature_with_hash(h.hexdigest(), sig_b64)
    except Exception as exc:
        logger.warning(f"signature verify failed: {exc}")
        return False


def download_update(info: dict, dest_dir: Path | None = None, progress_cb=None) -> str:
    """
    下载更新包并校验 MD5。
    progress_cb(downloaded_bytes, total_bytes)
    返回本地文件路径。校验失败抛 RuntimeError。
    """
    url = info["url"]
    md5 = (info.get("md5") or "").lower()
    dest_dir = Path(dest_dir) if dest_dir else _update_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0] or "update.zip"
    local = dest_dir / filename
    tmp = local.with_suffix(local.suffix + ".part")

    try:
        from src.security.sec_config import get_pinned_session
        with get_pinned_session(url).get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb:
                        progress_cb(done, total)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    if md5:
        h = hashlib.md5()
        with open(tmp, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != md5:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"MD5 校验失败: 期望 {md5}，实际 {h.hexdigest()}")

    # RSA 签名验证（P0-4 加固）：下载 <url>.sig 并用内置公钥验签
    # 验签失败 → 拒绝安装（防中间人 / 自建服务器投毒）
    if not _verify_rsa_signature(url, tmp):
        tmp.unlink(missing_ok=True)
        raise RuntimeError("更新包签名验证失败，已拒绝安装（可能被篡改或来源不可信）")

    tmp.replace(local)
    logger.info(f"update downloaded: {local} ({done} bytes)")
    return str(local)


def apply_update(zip_path: str | Path) -> tuple[bool, str]:
    """
    应用更新：
      1. 解压 zip 到 _update/new
      2. 生成 update.bat（等待退出 → 备份 → 替换 → 重启 → 自删）
      3. 启动 update.bat
    返回 (ok, message)。ok=True 后调用方应尽快退出主程序。
    """
    zip_path = Path(zip_path)
    if not zip_path.exists():
        return False, "更新包不存在"
    if not getattr(sys, "frozen", False):
        return False, "开发模式不支持自更新，请使用 git pull 更新源码"

    exe_dir = Path(sys.executable).parent          # .../7tan-editor/
    exe_name = Path(sys.executable).name            # 7tan-editor.exe
    upd_dir = _update_dir()
    new_dir = upd_dir / "new"

    # 解压
    try:
        if new_dir.exists():
            shutil.rmtree(new_dir, ignore_errors=True)
        new_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(new_dir)
    except Exception as exc:
        return False, f"解压失败: {exc}"

    # 定位 zip 内应用根目录（兼容 zip 内含 7tan-editor/ 目录或直接是文件）
    root = new_dir
    subs = [d for d in new_dir.iterdir() if d.is_dir()] if new_dir.exists() else []
    if len(subs) == 1 and (subs[0] / exe_name).exists():
        root = subs[0]
    if not (root / exe_name).exists():
        return False, f"更新包内未找到 {exe_name}"

    # 生成 update.bat —— 必须放在 exe_dir 的【父目录】！
    # 关键: bat 若位于 exe_dir 内部, ren exe_dir 时 cmd 正在执行的 bat 被移动,
    #       cmd 后续读取中止("The batch file cannot be found")导致更新卡死。
    bat = exe_dir.parent / "update.bat"
    try:
        bat.write_text(_bat_script(exe_dir, upd_dir, root, exe_name), encoding="utf-8")
    except Exception as exc:
        return False, f"写入更新脚本失败: {exc}"

    try:
        subprocess.Popen(
            [str(bat)],
            cwd=str(exe_dir.parent),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        return False, f"启动更新脚本失败: {exc}"

    logger.info(f"update applied, updater script: {bat}")
    return True, "更新程序已启动，软件即将重启"


def _bat_script(exe_dir: Path, upd_dir: Path, new_root: Path, exe_name: str) -> str:
    """生成 update.bat（放在 exe_dir 的父目录, 全英文注释, 兼容 chcp 65001 UTF-8）

    换名策略(关键):
      1. 先把新包 move 到旁路临时名 {exe_dir}.new
      2. ren 旧目录为 _old
      3. ren .new 为正式目录
      全程路径稳定; bat 在父目录, ren 不会移动正在执行的 bat。
    """
    old_dir = exe_dir.parent / f"{exe_dir.name}_old"
    new_dir = new_root.parent
    return f"""@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo [7Tan Updater] waiting for main process exit...
timeout /t 5 /nobreak >nul
taskkill /IM {exe_name} /F >nul 2>&1
timeout /t 2 /nobreak >nul

rem 1) stage new app beside current app (stable path)
move /y "{new_root}" "{exe_dir}.new" >nul
if errorlevel 1 goto :failed
if not exist "{exe_dir}.new\\{exe_name}" goto :failed

rem 2) retire old app
if exist "{old_dir}" rmdir /s /q "{old_dir}"
if exist "{exe_dir}" ren "{exe_dir}" 7tan-editor_old
if not exist "{old_dir}" goto :failed

rem 3) promote new app
ren "{exe_dir}.new" {exe_dir.name}
if not exist "{exe_dir}\\{exe_name}" goto :failed

rem 4) cleanup (exe_dir 已被改名, _update 现在位于 old_dir 下)
rmdir /s /q "{old_dir}" >nul 2>&1
rmdir /s /q "{old_dir}\\{UPDATE_DIR_NAME}\\new" >nul 2>&1
del /q "{old_dir}\\{UPDATE_DIR_NAME}\\*.zip" >nul 2>&1
del /q "{old_dir}\\{UPDATE_DIR_NAME}\\*.part" >nul 2>&1

start "" "{exe_dir}\\{exe_name}"
del "%~f0" >nul 2>&1
exit /b 0

:failed
echo [7Tan Updater] failed, rolling back...
if exist "{exe_dir}.new" (
    if exist "{exe_dir}" rmdir /s /q "{exe_dir}"
    ren "{exe_dir}.new" {exe_dir.name}
)
if not exist "{exe_dir}\\{exe_name}" (
    if exist "{old_dir}" ren "{old_dir}" {exe_dir.name}
)
del "%~f0" >nul 2>&1
exit /b 1
"""
