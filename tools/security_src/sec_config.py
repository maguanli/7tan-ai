"""
安全配置容器 — integrity 开关与敏感端点（AES-256-GCM 加密存储）
编译为 .pyd 后无法被反编译，保护完整性校验开关与服务器端点。
"""
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

_KEY_PART1 = b':\x7f,\x91\xe4\xb8U\r\xc6\xd2\x88\xfe\x17\xa3Ki'
_KEY_PART2 = b'\x8b\x1e_\xc3"\xd7\x9a@\xeea=\xb5\xf9\x04|\xa6'
_NONCE_PREFIX = b'\x7f\x4a\x2e\x91'


def _assemble_key() -> bytes:
    return _KEY_PART1 + _KEY_PART2


def _decrypt(encrypted_b64: str) -> str:
    if not encrypted_b64:
        return ""
    try:
        raw = base64.b64decode(encrypted_b64)
    except Exception:
        return ""
    if len(raw) < 12:
        return ""
    nonce = raw[:12]
    ct = raw[12:]
    try:
        return AESGCM(_assemble_key()).decrypt(nonce, ct, None).decode("utf-8")
    except Exception:
        return ""


# 加密值（构建时由 tools/gen_sec_config.py 注入）
_INTEGRITY_ENC = "'f0oukZftyqeSnWTrKzAJBtZbsP9PUd6fyW2wJXhHeFElqenR7cnWf0txaFF4HDo+LZzNECn2Z7nduLRmMWVW/ooRGNjSftnK8mhps4TitpcH/zmEXoCA5Le1Gdp0Phuve7NvgO8CTNshO+TuXu3e0EsT+nKsXzUQhDFL/JL4t70o2/nuWSLtBYe0tgV4GWEhohSou8GCINIuCW+bn4YpebaKE9FIOUU8XYjK8C8OJnwS2xiUl46Z27hIJEEzDn36pbVDY7kLNBRKOZHhJHIS/iI8SVdG4qzy5jZfqc5sdaCQVKjfGEXjUN6uC4JvhKr0'"
_UPDATE_ENC = "'f0ouket6PZmOmUlAmx9L5peI7fXksFEIkJv0YtOGLnYN1KGha4bYyBle/zRUmrcI/HwiXnuCEONyPpAB6ObtAKT1kdj7'"
_TELEMETRY_ENC = "'f0oukTqvuLGmbYoCBZr4yfLTFgd39xtrxQEGoakxgYIX4wQnsTnJ9QX27gGagdPB1qBVDWc60OGwz5ClZHKgno4u3O9y76Ty'"


def get_integrity_config() -> dict:
    """返回完整性校验的安全配置（不信任 config.yaml 明文）"""
    import json
    try:
        data = json.loads(_decrypt(_INTEGRITY_ENC) or "{}")
    except Exception:
        data = {}
    defaults = {
        "enabled": True, "mode": "core", "auto_repair": False,
        "developer_mode": False, "confirm_phrase": "我已知晓风险并信任此次修改",
        "show_status": True, "log_all_checks": True, "tamper_alert_email": "",
    }
    defaults.update({k: v for k, v in data.items() if v is not None})
    return defaults


def get_update_endpoint() -> str:
    return _decrypt(_UPDATE_ENC) or "https://www.7tan.com/api/update/check.php"


def get_telemetry_endpoint() -> str:
    return _decrypt(_TELEMETRY_ENC) or "https://www.7tan.com/api/telemetry/build.php"


def verify_update_signature(file_path: str, sig_b64: str, public_key_pem: str = None) -> bool:
    """验证更新包 RSA 签名（SHA-256 + PKCS1v15）"""
    try:
        if public_key_pem is None:
            from .strings import get_public_key
            public_key_pem = get_public_key()
        pub = load_pem_public_key(public_key_pem.encode("ascii"))
        sig = base64.b64decode(sig_b64)
        import hashlib
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        pub.verify(sig, h.digest(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def verify_update_signature_with_hash(sha256_hex: str, sig_b64: str, public_key_pem: str = None) -> bool:
    """验证更新包签名（基于预先计算的 SHA-256 摘要）"""
    try:
        if public_key_pem is None:
            from .strings import get_public_key
            public_key_pem = get_public_key()
        pub = load_pem_public_key(public_key_pem.encode("ascii"))
        sig = base64.b64decode(sig_b64)
        digest = bytes.fromhex(sha256_hex)
        pub.verify(sig, digest, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False
