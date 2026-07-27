"""
许可证验证模块
编译成 .pyd 后无法被反编译，保护授权验证逻辑。

验证流程:
    JWT Token → RSA 验签 → 检查过期 → 返回权限信息
"""
import time
from typing import Any

from .rsa_verify import rsa_verify
from .strings import get_public_key, get_api_url


# ============================================================
# 异常类
# ============================================================

class LicenseError(Exception):
    """许可证异常基类"""
    pass


class LicenseExpired(LicenseError):
    """授权已过期"""
    pass


class LicenseInvalid(LicenseError):
    """令牌无效（签名错误、格式错误等）"""
    pass


class LicenseNotPro(LicenseError):
    """非专业版用户"""
    pass


# ============================================================
# 公开 API
# ============================================================

def verify_license(token_str: str) -> dict[str, Any]:
    """
    验证授权令牌，返回用户权限信息。

    Args:
        token_str: JWT Token 字符串

    Returns:
        {
            "user_id": int,
            "username": str,
            "level": "basic" | "pro",
            "expires_at": int,       # Unix 时间戳
            "pro_activated": bool,
        }

    Raises:
        LicenseInvalid: 令牌格式错误或签名无效
        LicenseExpired: 授权已过期
    """
    if not token_str or not token_str.strip():
        raise LicenseInvalid("令牌为空")

    # 1. 获取公钥
    pub_key = get_public_key()
    if not pub_key:
        raise LicenseInvalid("系统配置错误：公钥缺失")

    # 2. RSA 验签
    try:
        payload = rsa_verify(token_str.strip(), pub_key)
    except ValueError as e:
        raise LicenseInvalid(str(e))

    # 3. 检查必要字段
    uid = payload.get("uid")
    if uid is None:
        raise LicenseInvalid("令牌缺少用户 ID")

    # 4. 检查过期
    now = int(time.time())
    exp = payload.get("exp", 0)
    if exp < now:
        raise LicenseExpired("授权已过期，请在 7tan.com 续费")

    # 5. 检查签发时间（防未来的令牌）
    iat = payload.get("iat", 0)
    if iat > now + 86400:
        raise LicenseInvalid("令牌签发时间异常")

    # 6. 判断会员等级
    pro_activated = payload.get("pro_activated", False)
    level = "pro" if pro_activated and (payload.get("pro_expires", 0) > now) else "basic"

    return {
        "user_id": uid,
        "username": payload.get("username", ""),
        "level": level,
        "expires_at": exp,
        "pro_activated": pro_activated,
    }


def is_pro(token_str: str) -> bool:
    """
    检查是否为专业版用户。

    Args:
        token_str: JWT Token

    Returns:
        True 如果是专业版且未过期
    """
    try:
        result = verify_license(token_str)
        return result["level"] == "pro"
    except LicenseError:
        return False


def get_license_info(token_str: str) -> dict[str, Any]:
    """
    获取许可证信息（不抛异常版本）。

    Args:
        token_str: JWT Token

    Returns:
        {
            "valid": bool,
            "level": "basic" | "pro" | "expired" | "invalid",
            "user_id": int or None,
            "username": str,
            "error": str or None,
        }
    """
    try:
        result = verify_license(token_str)
        return {
            "valid": True,
            "level": result["level"],
            "user_id": result["user_id"],
            "username": result["username"],
            "error": None,
        }
    except LicenseExpired:
        return {
            "valid": False,
            "level": "expired",
            "user_id": None,
            "username": "",
            "error": "授权已过期",
        }
    except LicenseInvalid as e:
        return {
            "valid": False,
            "level": "invalid",
            "user_id": None,
            "username": "",
            "error": str(e),
        }
