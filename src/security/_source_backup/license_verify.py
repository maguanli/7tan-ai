"""
许可证验证模块
编译成 .pyd 后无法被反编译，保护授权验证逻辑。

验证流程:
    JWT Token → RSA 验签 → 检查过期 → 返回权限信息
"""
import base64
import json
import time
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key as _load_pubkey

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

def verify_license(pro_license: str) -> dict[str, Any]:
    """
    验证 PRO License（RSA 签名），返回权限信息。

    License 格式: base64url(signature).base64url(payload)
    Payload: {"uid":int, "level":"pro", "pro_expires":int, "issued_at":int}

    Args:
        pro_license: RSA 签名的 PRO 授权凭证字符串

    Returns:
        {
            "user_id": int,
            "level": "pro",
            "pro_expires": int,
            "issued_at": int,
        }

    Raises:
        LicenseInvalid: 格式错误、签名无效或公钥缺失
        LicenseExpired: 授权已过期
        LicenseNotPro: 非专业版凭证
    """
    if not pro_license or not isinstance(pro_license, str) or not pro_license.strip():
        raise LicenseInvalid("授权凭证为空")

    # 1. 获取公钥
    pub_key = get_public_key()
    if not pub_key:
        raise LicenseInvalid("系统配置错误：公钥缺失")

    # 2. 解析 License（格式: sig.payload）
    parts = pro_license.strip().split(".")
    if len(parts) != 2:
        raise LicenseInvalid("授权凭证格式无效")

    sig_b64, payload_b64 = parts

    try:
        signature = base64.urlsafe_b64decode(sig_b64 + "==")
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
    except Exception:
        raise LicenseInvalid("授权凭证解码失败")

    # 3. RSA 验签
    try:
        public_key = _load_pubkey(pub_key.encode("ascii"))
        public_key.verify(
            signature,
            payload_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception as e:
        raise LicenseInvalid(f"签名验证失败: {e}")

    # 4. 解析 payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise LicenseInvalid("授权凭证内容解析失败")

    # 5. 检查必要字段
    uid = payload.get("uid")
    if uid is None:
        raise LicenseInvalid("凭证缺少用户 ID")

    level = payload.get("level", "")
    if level != "pro":
        raise LicenseNotPro("非专业版授权凭证")

    # 6. 检查过期
    now = int(time.time())
    pro_expires = payload.get("pro_expires", 0)
    if pro_expires < now:
        raise LicenseExpired("PRO 授权已过期，请在 7tan.com 续费")

    return {
        "user_id": uid,
        "level": "pro",
        "pro_expires": pro_expires,
        "issued_at": payload.get("issued_at", 0),
        "username": payload.get("username", ""),
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
            "level": "free" | "pro" | "expired" | "invalid",
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
            "username": result.get("username", ""),
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
