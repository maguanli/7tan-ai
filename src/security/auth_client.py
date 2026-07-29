"""
7tan.com API 客户端
负责与网站后端通信：登录、验证 Token、刷新 Token。
"""
import time
from typing import Optional

import requests
from loguru import logger

from .strings import get_api_url

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
# 公开 API
# ============================================================

def login(username: str, password: str, remember_me: bool = False) -> dict:
    """
    登录 7tan.com，获取 JWT Token。

    Args:
        username: 用户名或手机号
        password: 密码（明文，HTTPS 传输）
        remember_me: 是否记住登录（30天有效期）

    Returns:
        {
            "token": "eyJhbGci...",       # JWT Token
            "user_id": 123,
            "username": "player1",
            "level": "basic",             # basic / pro
            "pro_expires": 1735689600,    # 专业版到期时间（0=未开通）
            "expires_in": 2592000,        # Token 有效期（秒）
        }

    Raises:
        LoginFailed: 用户名或密码错误
        NetworkError: 网络连接失败
        ServerError: 服务器错误
    """
    url = get_api_url("login")
    if not url:
        raise ServerError("API 端点未配置")

    payload = {
        "username": username.strip(),
        "password": password,
        "remember": 1 if remember_me else 0,
    }

    try:
        resp = requests.post(url, json=payload, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"网络连接失败: {e}")

    if resp.status_code != 200:
        raise ServerError(f"服务器返回 {resp.status_code}")

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
            "level": "basic" / "pro" / "expired",
            "pro_expires": 1735689600,
            "error": None / "错误信息",
        }
    """
    url = get_api_url("verify")
    if not url:
        return {"valid": False, "level": "unknown", "error": "API 端点未配置"}

    try:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as e:
        logger.warning(f"[Auth] 在线验证失败: {e}")
        return {"valid": False, "level": "unknown", "error": f"网络异常: {e}"}

    if resp.status_code != 200:
        return {"valid": False, "level": "unknown", "error": f"服务器错误 ({resp.status_code})"}

    try:
        data = resp.json()
    except Exception:
        return {"valid": False, "level": "unknown", "error": "数据格式异常"}

    return {
        "valid": data.get("success", False),
        "level": data.get("level", "basic"),
        "pro_expires": data.get("pro_expires", 0),
        "error": data.get("message") if not data.get("code") == 0 else None,
    }


def refresh_token(token: str) -> dict:
    """
    刷新 Token（续费/升级后使用）。
    先尝试 GET + Authorization header，失败则尝试 POST body。

    Args:
        token: 当前 JWT Token

    Returns:
        {"success": True, "token": "new_token", "level": "pro", ...}
    """
    url = get_api_url("refresh")
    if not url:
        return {"success": False, "message": "API 端点未配置"}

    def _do_request(method: str) -> dict:
        """执行单次请求并解析结果"""
        try:
            if method == "GET":
                resp = requests.get(
                    url,
                    params={"token": token},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=_TIMEOUT,
                )
            else:
                resp = requests.post(
                    url,
                    json={"token": token},
                    headers={"Authorization": f"Bearer {token}"},
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
            "level": data.get("level", "basic"),
            "pro_expires": data.get("pro_expires", 0),
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
    from .strings import get_api_url
    url = get_api_url("trial")
    if not url:
        return {"success": False, "error": "试用 API 端点未配置", "trials_left": 0}

    try:
        resp = requests.post(
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
