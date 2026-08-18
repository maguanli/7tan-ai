"""
密码与敏感信息加密存储模块
使用 AES-256-GCM 加密，密钥从机器指纹派生
"""
import base64
import hashlib
import json
import os
import platform
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _machine_fingerprint() -> bytes:
    """生成机器指纹作为密钥派生种子"""
    parts = [
        platform.node(),
        platform.processor() or "",
        str(uuid.getnode()),
    ]
    return hashlib.sha256("|".join(parts).encode()).digest()


def _derive_key(salt: bytes = None) -> tuple:
    """从机器指纹派生 AES-256 密钥"""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", _machine_fingerprint(), salt, 100000, dklen=32)
    return key, salt


def encrypt(plaintext: str) -> str:
    """加密字符串，返回 base64 编码的密文"""
    key, salt = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # 格式: salt(16) + nonce(12) + ciphertext
    combined = salt + nonce + ciphertext
    return base64.b64encode(combined).decode("ascii")


def decrypt(encoded: str) -> str:
    """解密 base64 编码的密文"""
    try:
        combined = base64.b64decode(encoded)
        salt = combined[:16]
        nonce = combined[16:28]
        ciphertext = combined[28:]
        key, _ = _derive_key(salt)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception:
        return ""


def encrypt_dict(data: dict, keys: list) -> dict:
    """对字典中指定 key 的值加密"""
    result = data.copy()
    for k in keys:
        if k in result and result[k]:
            result[k] = encrypt(str(result[k]))
    return result


def decrypt_dict(data: dict, keys: list) -> dict:
    """对字典中指定 key 的值解密"""
    result = data.copy()
    for k in keys:
        if k in result and result[k]:
            try:
                result[k] = decrypt(result[k])
            except Exception:
                pass
    return result
