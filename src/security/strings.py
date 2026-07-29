"""
敏感字符串加密存储模块

RSA 公钥、API 端点 URL 等敏感字符串使用 AES-256-GCM 加密存储，
运行时解密。防止 strings 命令一键提取明文。

密钥分两半分散存储，增加逆向难度。
"""
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ============================================================
# 内置解密密钥（16 字节 + 16 字节 = 32 字节 AES-256）
# 分两半存储，防止连续字节扫描
# ============================================================

_KEY_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'
_KEY_PART2 = b'\x8b\x1e\x5f\xc3\x22\xd7\x9a\x40\xee\x61\x3d\xb5\xf9\x04\x7c\xa6'

# Nonce 前缀（固定部分 + 随机部分）
_NONCE_PREFIX = b'\x7f\x4a\x2e\x91'


def _assemble_key() -> bytes:
    """组装 AES-256 密钥"""
    return _KEY_PART1 + _KEY_PART2


# ============================================================
# 加密字符串存储区
# 格式: AES-256-GCM(nonce=12, ciphertext+tag) → base64
# 使用 tools/encrypt_strings.py 生成
# ============================================================

# 占位符 — 实际值由 tools/encrypt_strings.py 生成后替换
_STORE: dict[str, str] = {
    "public_key": "f0oukbh2fUnO3KudoG0bAG1sIlGnl+O4j5Z9ATGcqj9/Hv1WC6RxLRN+UHk67S/tR7zxncxCxOY73kyFtzMqjadXvm2J/7V7EQE/+Af5ya01TMUtBn00dZIFj6jtSaX9wJYkxh/8qs5m1CRaOC9q34vIJtqJxRxgIdrIcnZRT8RvTkfwOY0yw+d7F95szj0QxDxiNfpCbq9HHHp/39Q4eJ4RwVpLoz6S5lHkE3QeJ+jkVypiHpuCPJbl1YCD6VrcHdG9KANj+IMYlwbIdZ26iIdvSbFKvGAODPZgVezzmvMUU+N0sARMrzl5yLwKG966aOIi5s5PUoYGtkR7cBVsJd1d1ePQwp5c2PisRRzRaTkUbgq1i5Q3LVZElxNwGsdu5R6kkLFlQ/50+GwLAMSKA4t7GIUEpm0ZaUyHMGKmyIju65DSQgWpu2oQMa4oUUvJuSCtVCkq2u6bauG7od+RR3IBXPWIn90h+fWDRoVxQQsiPqyOtc4U7XxnjzJBZJ4Yicy8Sa0h39rX6C37G9kJ2FR1r9M0aGZkMsLnqbdeK+GUeBSVsLyeyiqJQ3IzPM2+56oTtnO31ZWNNS6PbTDc6gms8KaTS3jZi45qwNrOV+olCGVlljvJSiHdRIrjrJE=",
    "api_login": "f0oukeI60CyaF4xSQuFAaLx/+/MQy9U9iolB2YZspQAlxBhbJLJ9ZhtdgZRnpLBvXOGXMDbHnJmCI3zT/KU0CL2INA==",
    "api_verify": "f0oukeNPxGFI9rD8A/tDGFwDpb6G7ehmHhh9g4CvjSwxDONCvQQ/JP+CMQ16LqQ+h33z5Kq/yxZQ/ycarpBgJjLzx7Y=",
    "api_refresh": "f0oukYIxG7j3yl5rQOlyGihuq1P1bAzz62D2YburpeQPBpFOfea8SmXTcDa9aQMBt8I+smPbA/ME0pf9xup9B/XuE+to=",
    "api_trial": "f0oukQ+SglMVIv9Mo7iNRxBuniB5HNZSzzOruUMP+u/iulzhIzy0GPkDtSwV7SUhVi7iPhYrpLpQhyxeSMwGK2Y=",   # AI 试用代理端点 https://img.7tan.cn/api/ai/trial.php
}


# ============================================================
# 解密函数
# ============================================================

def _decrypt(encrypted_b64: str) -> str:
    """
    解密 AES-256-GCM 加密的敏感字符串。

    加密格式: nonce(12字节) + ciphertext_and_tag
    nonce = _NONCE_PREFIX(4字节) + random(8字节)
    """
    if not encrypted_b64:
        return ""

    try:
        raw = base64.b64decode(encrypted_b64)
    except Exception:
        return ""

    if len(raw) < 12:
        return ""

    nonce = raw[:12]
    ciphertext_with_tag = raw[12:]

    try:
        aesgcm = AESGCM(_assemble_key())
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext.decode("utf-8")
    except Exception:
        return ""


# ============================================================
# 公开 API
# ============================================================

def get_public_key() -> str:
    """获取 RSA 公钥（PEM 格式）"""
    return _decrypt(_STORE.get("public_key", ""))


def get_api_url(endpoint: str) -> str:
    """
    获取 API 端点 URL。

    Args:
        endpoint: "login" / "verify" / "refresh" / "trial"

    Returns:
        完整的 HTTPS URL，解密失败返回空字符串
    """
    key_map = {
        "login": "api_login",
        "verify": "api_verify",
        "refresh": "api_refresh",
        "trial": "api_trial",
    }
    store_key = key_map.get(endpoint, "")
    if not store_key:
        return ""
    return _decrypt(_STORE.get(store_key, ""))


def set_encrypted_value(key: str, encrypted_b64: str) -> None:
    """
    设置加密值（供 tools/encrypt_strings.py 调用）。

    Args:
        key: 键名 (public_key / api_login / api_verify / api_refresh)
        encrypted_b64: AES 加密后的 base64 字符串
    """
    if key in _STORE:
        _STORE[key] = encrypted_b64
