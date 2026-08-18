"""
7tan.com API 客户端
负责与网站后端通信：登录、验证 Token、刷新 Token、试用代理、资源发布。

安全特性:
  - P1-5: 登录携带设备指纹（device_id/fingerprint/device_name/os_info），token 绑定设备
  - P2-10: 所有请求使用 TLS 证书固定（get_pinned_session），防中间人/自建服务器劫持
"""
import time
from typing import Optional

import requests
from loguru import logger

from .strings import get_api_url


def _get_site_base_url() -> str:
    """从配置获取 7tan 后台基础 URL"""
    try:
        from ..config.loader import load_config
        config = load_config()
        return config.get("site_7tan", {}).get("base_url", "")
    except Exception:
        return ""


def _get_api_url(endpoint: str) -> str:
    """获取 API 端点 URL：内置官方端点优先（www.7tan.com/api/*）。

    内置端点为空时才回退到 config 的 base_url（兼容自建服务器）。
    修复：config base_url 指向管理后台域名（img.7tan.cn），
    直接传 fallback 会把 API 请求拼到错误域名导致 404。
    """
    url = get_api_url(endpoint)
    if not url:
        url = get_api_url(endpoint, fallback_base=_get_site_base_url())
    return url


# ============================================================
# 超时配置
# ============================================================
_TIMEOUT = 15  # 请求超时（秒）


# ============================================================
# 异常类
# ============================================================

class AuthError(Exception):
    """认证异常基类"""
    pass


class LoginFailed(AuthError):
    """登录失败（用户名或密码错误）"""
    pass


class NetworkError(AuthError):
    """网络错误"""
    pass


class ServerError(AuthError):
    """服务器错误"""
    pass


# ============================================================
# 设备指纹采集（P1-5）
# ============================================================

def _collect_device_info() -> dict:
    """采集设备指纹，用于登录时绑定 token 到设备。

    失败时返回空 dict（不影响登录，向后兼容）。
    返回: {"device_id", "fingerprint", "device_name", "os_info"}
    """
    try:
        from .device_fingerprint import collect_fingerprint
        info = collect_fingerprint()
        if isinstance(info, dict) and info.get("device_id"):
            return {
                "device_id": str(info.get("device_id", "")),
                "fingerprint": str(info.get("fingerprint", "")),
                "device_name": str(info.get("device_name", "")),
                "os_info": str(info.get("os_info", "")),
            }
    except Exception:
        logger.debug("[Auth] 设备指纹采集失败（忽略，不阻断登录）", exc_info=True)
    return {}


# ============================================================
# 公开 API
# ============================================================

def login(username: str, password: str, remember_me: bool = False, device_info: dict = None) -> dict:
    """
    登录 7tan.com，获取 JWT Token。

    Args:
        username: 用户名或手机号
        password: 密码（明文，HTTPS 传输）
        remember_me: 是否记住登录（30天有效期）
        device_info: 设备指纹 dict（可选，默认自动采集）

    Returns:
        {
            "token": "eyJhbGci...",       # JWT Token
            "user_id": 123,
            "username": "player1",
            "level": "free",             # free / pro
            "pro_expires": 1735689600,    # 专业版到期时间（0=未开通）
            "expires_in": 2592000,        # Token 有效期（秒）
        }

    Raises:
        LoginFailed: 用户名或密码错误
        NetworkError: 网络连接失败
        ServerError: 服务器错误
    """
    url = _get_api_url("login")
    if not url:
        raise ServerError("API 端点未配置")

    payload = {
        "username": username.strip(),
        "password": password,
        "remember": 1 if remember_me else 0,
    }

    # P1-5: 携带设备指纹（token 绑定设备，防共享/转卖）
    dev = device_info if isinstance(device_info, dict) else _collect_device_info()
    if dev:
        payload["device_id"] = dev.get("device_id", "")
        payload["fingerprint"] = dev.get("fingerprint", "")
        payload["device_name"] = dev.get("device_name", "")
        payload["os_info"] = dev.get("os_info", "")

    try:
        from .sec_config import get_pinned_session
        resp = get_pinned_session(url).post(url, json=payload, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"网络连接失败: {e}")

    if resp.status_code != 200:
        # 尝试解析服务器返回的中文错误信息（401=凭据错误，如"账号或密码错误"）
        try:
            _raw = resp.json()
            _msg = _raw.get("message", "") or ""
        except Exception:
            _msg = (resp.text or "")[:200]
        if resp.status_code == 401:
            raise LoginFailed(_msg or "账号或密码错误")
        raise ServerError(_msg or f"服务器返回 {resp.status_code}")

    try:
        data = resp.json()
    except Exception:
        raise ServerError("服务器返回数据格式异常")

    if not data.get("code") == 0:
        msg = data.get("message", "登录失败")
        raise LoginFailed(msg)

    user_data = data.get("data", {})
    token = user_data.get("token", "")
    if not token:
        raise ServerError("服务器未返回 Token")

    return {
        "token": token,
        "user_id": user_data.get("user", {}).get("uid", 0),
        "username": user_data.get("user", {}).get("username", username),
        "level": user_data.get("user", {}).get("level", "free"),
        "pro_expires": user_data.get("user", {}).get("pro_expires", 0),
        "expires_in": 2592000,
        "trial_ai_count": user_data.get("user", {}).get("trial_ai_count", 0),
        "pro_license": user_data.get("pro_license", ""),
    }


def online_verify(token: str) -> dict:
    """
    在线验证 Token 有效性，获取最新会员状态。
    用于续费后刷新状态。

    Args:
        token: JWT Token

    Returns:
        {
            "valid": True/False,
            "level": "free" / "pro" / "expired",
            "pro_expires": 1735689600,
            "error": None / "错误信息",
        }
    """
    url = _get_api_url("verify")
    if not url:
        return {"valid": False, "level": "unknown", "error": "API 端点未配置"}

    try:
        from .sec_config import get_pinned_session
        resp = get_pinned_session(url).get(url, headers={"Authorization": f"Bearer {token}"}, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as e:
        logger.warning(f"[Auth] 在线验证失败: {e}")
        return {"valid": False, "level": "unknown", "error": f"网络异常: {e}"}

    if resp.status_code != 200:
        return {"valid": False, "level": "unknown", "error": f"服务器错误 ({resp.status_code})"}

    try:
        data = resp.json()
    except Exception:
        return {"valid": False, "level": "unknown", "error": "数据格式异常"}

    inner = data.get("data") or {}
    ok = (data.get("code") == 0) and bool(inner)
    return {
        "valid": ok,
        "level": inner.get("level", "free"),
        "pro_expires": inner.get("pro_expires", 0),
        "error": None if ok else (data.get("message") or "验证失败"),
    }


def refresh_token(token: str, device_id: str = "") -> dict:
    """
    刷新 Token（续费/升级后使用）。
    先尝试 GET + Authorization header，失败则尝试 POST body。
    携带 device_id（P1-5：刷新时校验设备，专业版换设备将被服务器拒绝）。

    Args:
        token: 当前 JWT Token
        device_id: 当前设备 ID（可选；不传则向后兼容，服务器放行）

    Returns:
        {"success": True, "token": "new_token", "level": "pro", ...}
    """
    url = _get_api_url("refresh")
    if not url:
        return {"success": False, "message": "API 端点未配置"}

    def _do_request(method: str) -> dict:
        """执行单次请求并解析结果"""
        try:
            from .sec_config import get_pinned_session
            _sess = get_pinned_session(url)
            _headers = {"Authorization": f"Bearer {token}"}
            if device_id:
                _headers["X-Device-Id"] = device_id
            if method == "GET":
                resp = _sess.get(
                    url,
                    params={"token": token, "device_id": device_id},
                    headers=_headers,
                    timeout=_TIMEOUT,
                )
            else:
                resp = _sess.post(
                    url,
                    json={"token": token, "device_id": device_id},
                    headers=_headers,
                    timeout=_TIMEOUT,
                )
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"网络异常: {e}"}

        # 尝试解析服务器消息
        try:
            raw = resp.json()
            server_msg = raw.get("message", "")
        except Exception:
            server_msg = (resp.text or "")[:200]

        if resp.status_code != 200:
            detail = server_msg or f"HTTP {resp.status_code}"
            return {"success": False, "message": f"服务器错误: {detail}"}

        if raw.get("code") != 0:
            return {"success": False, "message": raw.get("message", "刷新失败")}

        data = raw.get("data", {})
        return {
            "success": True,
            "token": data.get("token", ""),
            "level": data.get("level", "free"),
            "pro_expires": data.get("pro_expires", 0),
            "pro_license": data.get("pro_license", ""),
        }

    # 先尝试 GET
    result = _do_request("GET")
    if result.get("success"):
        return result

    # GET 失败，尝试 POST（某些服务器配置可能不传 query string）
    logger.info("[Auth] GET 刷新失败，尝试 POST...")
    return _do_request("POST")


# ============================================================
# 试用 AI 代理调用（通过 7tan.com 服务端转发 DeepSeek）
# ============================================================

def trial_call(token: str, model: str, messages: list) -> dict:
    """
    通过服务端代理调用 AI（试用模式，服务端计次防羊毛）。

    Args:
        token: JWT Token
        model: 模型名称（如 deepseek-chat）
        messages: OpenAI 格式的消息列表

    Returns:
        {
            "success": True/False,
            "choices": [...],          # OpenAI 格式的 choices
            "usage": {...},            # token 用量
            "trials_left": int,        # 剩余试用次数
            "error": str or None,      # 错误信息
        }
    """
    url = _get_api_url("trial")
    if not url:
        return {"success": False, "error": "试用 API 端点未配置", "trials_left": 0}

    try:
        from .sec_config import get_pinned_session
        resp = get_pinned_session(url).post(
            url,
            json={"token": token, "model": model, "messages": messages},
            timeout=120,  # AI 调用较慢
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f"[Trial] AI 代理请求失败: {e}")
        return {"success": False, "error": f"网络异常: {e}", "trials_left": -1}

    try:
        data = resp.json()
    except Exception:
        return {"success": False, "error": "服务器返回数据格式异常", "trials_left": -1}

    if resp.status_code == 402:
        # 试用次数用完
        return {
            "success": False,
            "error": data.get("message", "AI 试用次数已用完"),
            "trials_left": 0,
        }

    if data.get("code") != 0:
        return {
            "success": False,
            "error": data.get("message", "AI 调用失败"),
            "trials_left": data.get("data", {}).get("trials_left", -1),
        }

    result = data.get("data", {})
    return {
        "success": True,
        "choices": result.get("choices", []),
        "usage": result.get("usage"),
        "trials_left": result.get("trials_left", -1),
        "error": None,
    }


# ============================================================
# 资源发布 API（替代浏览器自动化发布）
# ============================================================

def api_publish_resource(
    token: str,
    title: str,
    intro: str,
    download_url: str,
    category: str = "",
    tags: str = "",
    resource_type: str = "game",
    logo_path: str = "",
    screenshot_paths: list = None,
    platform: str = "Android",
    system_version: str = "5.0",
    developer: str = "官方",
) -> dict:
    """
    通过 API 发布资源到 7tan 网站（替代浏览器自动化）。

    Args:
        token: JWT Token（管理员认证）
        title: 资源标题
        intro: 简介/正文（HTML）
        download_url: 下载链接（OSS 外链）
        category: 分类名称
        tags: 标签（逗号分隔）
        resource_type: 'game' 或 'software'
        logo_path: 本地 LOGO 文件路径
        screenshot_paths: 本地截图文件路径列表
        platform: 平台（Android/iOS/PC）
        system_version: 系统版本要求
        developer: 开发商

    Returns:
        {
            "success": True/False,
            "message": "...",
            "publish_id": 123,
            "publish_url": "https://...",
        }
    """
    url = _get_api_url("publish")
    if not url:
        return {
            "success": False,
            "message": "发布 API 端点未配置，请在服务端部署 api/publish.php",
            "fallback": "browser",
        }

    headers = {"Authorization": f"Bearer {token}"}

    try:
        # 使用 multipart/form-data 上传
        import os as _os

        # 准备表单数据
        form_data = {
            "title": title,
            "intro": intro,
            "download_url": download_url,
            "category": category,
            "tags": tags,
            "resource_type": resource_type,
            "platform": platform,
            "system_version": system_version,
            "developer": developer,
        }

        # 准备文件
        files = []
        if logo_path and _os.path.exists(logo_path):
            files.append(("logo", (_os.path.basename(logo_path),
                                   open(logo_path, "rb"),
                                   "image/png" if logo_path.endswith(".png") else "image/jpeg")))

        if screenshot_paths:
            for i, sp in enumerate(screenshot_paths):
                if _os.path.exists(sp):
                    files.append(
                        (f"screenshot_{i}",
                         (_os.path.basename(sp),
                          open(sp, "rb"),
                          "image/png" if sp.endswith(".png") else "image/jpeg"))
                    )

        try:
            from .sec_config import get_pinned_session
            resp = get_pinned_session(url).post(
                url,
                data=form_data,
                files=files,
                headers=headers,
                timeout=120,  # 上传大文件需要较长时间
            )
        finally:
            # 关闭所有打开的文件
            for _, (_, fh, _) in files:
                fh.close()

        if resp.status_code != 200:
            return {
                "success": False,
                "message": f"服务器返回 {resp.status_code}: {resp.text[:200]}",
            }

        try:
            data = resp.json()
        except Exception:
            return {
                "success": False,
                "message": f"服务器返回数据格式异常: {resp.text[:200]}",
            }

        if data.get("code") == 0:
            result_data = data.get("data", {})
            return {
                "success": True,
                "message": data.get("message", "发布成功"),
                "publish_id": result_data.get("id", 0),
                "publish_url": result_data.get("url", ""),
            }
        else:
            return {
                "success": False,
                "message": data.get("message", "发布失败"),
                "error_code": data.get("code", -1),
            }

    except Exception as e:
        logger.error(f"[API Publish] 请求失败: {e}")
        return {
            "success": False,
            "message": f"网络异常: {e}",
            "fallback": "browser",
        }


def api_login_for_admin(username: str, password: str) -> dict:
    """
    管理员 API 登录 — 获取 Token 并自动加密存储到数据库。

    这是 login_7tan 的 API 替代方案。
    登录成功后 Token 自动持久化，后续 publish_to_7tan 可免密码运行。

    Args:
        username: 管理员用户名
        password: 管理员密码（HTTPS 传输，不落盘）

    Returns:
        {"success": True/False, "message": "...", "token": "..."}
    """
    try:
        result = login(username, password)
        token = result.get("token", "")

        if token:
            # 加密存储 Token 到数据库
            from ..database.db import store_admin_token, save_site_credential
            store_admin_token(token, result.get("expires_in", 2592000))
            save_site_credential(
                site="7tan_admin",
                username=username,
                api_base_url=_get_site_base_url(),
            )
            logger.info(f"[Auth] 管理员 Token 已存储（有效期 {result.get('expires_in', 2592000)} 秒）")
            return {
                "success": True,
                "message": "登录成功，Token 已加密存储",
                "token": token,
                "level": result.get("level", "free"),
            }
        else:
            return {"success": False, "message": "登录成功但未获取到 Token"}

    except LoginFailed as e:
        return {"success": False, "message": f"登录失败: {e}"}
    except NetworkError as e:
        return {"success": False, "message": f"网络错误: {e}"}
    except Exception as e:
        return {"success": False, "message": f"未知错误: {e}"}
