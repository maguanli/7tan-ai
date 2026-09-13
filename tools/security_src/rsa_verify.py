"""
RSA 签名验证引擎
编译成 .pyd 后无法被反编译，保护验签逻辑

支持 JWT RS256 (RSA-PKCS1v15 + SHA-256) 验签。
"""
import base64
import json
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key


# ============================================================
# 公开 API
# ============================================================

def rsa_verify(token_str: str, public_key_pem: str) -> dict[str, Any]:
    """
    验证 JWT Token 的 RSA 签名，返回解码后的 payload。

    Args:
        token_str: JWT 字符串 (header.payload.signature)
        public_key_pem: PEM 格式 RSA 公钥

    Returns:
        payload 字典，包含 uid、level、exp、iat 等字段

    Raises:
        ValueError: 签名无效或令牌格式错误
    """
    parts = token_str.strip().split(".")
    if len(parts) != 3:
        raise ValueError("令牌格式无效：需要 header.payload.signature")

    header_b64, payload_b64, sig_b64 = parts

    # 还原签名
    sig_bytes = _base64url_decode(sig_b64)

    # 构造待验证消息
    message = f"{header_b64}.{payload_b64}".encode("ascii")

    # 加载公钥
    try:
        public_key = load_pem_public_key(public_key_pem.encode("ascii"))
    except Exception as e:
        raise ValueError(f"公钥加载失败: {e}")

    # 验证签名
    try:
        public_key.verify(
            sig_bytes,
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception:
        raise ValueError("签名验证失败，令牌可能被篡改")

    # 解码 payload
    try:
        payload_json = _base64url_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Payload 解析失败: {e}")

    return payload


# ============================================================
# 内部辅助
# ============================================================

def _base64url_decode(data: str) -> bytes:
    """
    Base64URL 解码。

    JWT 使用 Base64URL（- 替代 +，_ 替代 /，无 = 填充），
    需要先还原为标准 Base64 再解码。
    """
    # 还原 Base64URL → 标准 Base64
    data = data.replace("-", "+").replace("_", "/")
    # 补齐填充
    remainder = len(data) % 4
    if remainder:
        data += "=" * (4 - remainder)
    return base64.b64decode(data)
