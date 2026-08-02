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
_INTEGRITY_ENC = "'f0oukTE0B8fNAaXV4WlkA5vk/nXyLOHnxdi9U4idc13cLuaHP6L502pIlxclQynDbT0fhzf43gzKjeUWyy8kIrLdGUjomiKhQeMDy52dD/RsoIpI/ESftWJUNAzdF46PSzSgTU9x5mcolBSKQ9byEirxPlJCXwbJ9Obo51BLkda51ECUJKTvbYNGHd81xkjZq6ngEaWKjE1hvfflDQ+K82hM9scf7Sk7SYcjloo/ju3sWLXeSKwOeB0BcIpjJLjVx003vgLP7dL+6rWyX4R0uiheNiz1c/x82gNSeaPFINAmvAgQRU7TH7y3wIbi9aLN'"
_UPDATE_ENC = "'f0oukSUW2+B6r8ycDhzpK/hwUov6toA9XkGuIZ3WyluCHoXjm5UPZmaI4zn+AobtjKB0iHmJa8FwO/1Fmw/KazaCo0WD'"
_TELEMETRY_ENC = "'f0oukZ3HxKY6jNpAPo2YZZ9DIgIUp2f1NvhIRLqWQRCBY6ZsBB9XLe1ZRdca7owqEG0qZmkgtNNfgj1bKQPezAnx3VxoxSri'"
_ENC_SEED_ENC = "'f0oukUpk6+cQpk0IJXOnIC7A2Hia336HppC9nf98HkUK40/8AVRA83zu6y0ujr82X8FLdPGRZNhF/KyfNLAcLHi4M+0Qd5AR2r/EPEUv20LscyQoYccK90W3vNs='"


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


def get_encryption_seed() -> bytes:
    """返回本地密钥派生种子（P1-6b：AES-256-GCM 解密，不落盘）

    用于 db.py 的 Fernet 密钥派生（新安装用户），
    攻击者仅凭 config.yaml / 源码无法推断出该种子，需逆向 pyd。
    """
    s = _decrypt(_ENC_SEED_ENC)
    if not s:
        return b"7Tan-Default-Seed-2026"
    return s.encode("utf-8")


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
