#!/usr/bin/env python3
"""生成 sec_config.py — 加密 integrity 开关 + 敏感端点

用法: python tools/gen_sec_config.py
"""
import base64, secrets, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "security" / "sec_config.py"

# 与 strings.py / encrypt_strings.py 相同的密钥与 nonce 前缀
_KEY_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'
_KEY_PART2 = b'\x8b\x1e\x5f\xc3\x22\xd7\x9a\x40\xee\x61\x3d\xb5\xf9\x04\x7c\xa6'
_NONCE_PREFIX = b'\x7f\x4a\x2e\x91'
KEY = _KEY_PART1 + _KEY_PART2


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    nonce = _NONCE_PREFIX + secrets.token_bytes(8)
    aesgcm = AESGCM(KEY)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def build_py() -> str:
    integrity_json = (
        '{"enabled": true, "mode": "core", "auto_repair": false, '
        '"developer_mode": false, "confirm_phrase": "我已知晓风险并信任此次修改", '
        '"show_status": true, "log_all_checks": true, "tamper_alert_email": ""}'
    )
    enc_integrity = encrypt(integrity_json)
    enc_update = encrypt("https://www.7tan.com/api/update/check.php")
    enc_telemetry = encrypt("https://www.7tan.com/api/telemetry/build.php")

    py = '''"""
安全配置容器 — integrity 开关与敏感端点（AES-256-GCM 加密存储）
编译为 .pyd 后无法被反编译，保护完整性校验开关与服务器端点。
"""
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

_KEY_PART1 = _KEY_PART1_
_KEY_PART2 = _KEY_PART2_
_NONCE_PREFIX = b'\\x7f\\x4a\\x2e\\x91'


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
_INTEGRITY_ENC = "_INTEGRITY_ENC_"
_UPDATE_ENC = "_UPDATE_ENC_"
_TELEMETRY_ENC = "_TELEMETRY_ENC_"


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
'''
    py = py.replace("_KEY_PART1_", repr(_KEY_PART1))
    py = py.replace("_KEY_PART2_", repr(_KEY_PART2))
    py = py.replace("_INTEGRITY_ENC_", repr(enc_integrity))
    py = py.replace("_UPDATE_ENC_", repr(enc_update))
    py = py.replace("_TELEMETRY_ENC_", repr(enc_telemetry))
    return py


def main():
    content = build_py()
    OUT.write_text(content, encoding="utf-8")
    print(f"✅ 已生成: {OUT} ({len(content)} bytes)")
    # 自检
    sys.path.insert(0, str(ROOT / "src"))
    import importlib
    import src.security.sec_config as sc
    importlib.reload(sc)
    cfg = sc.get_integrity_config()
    print("  integrity:", cfg)
    print("  update:", sc.get_update_endpoint())
    print("  telemetry:", sc.get_telemetry_endpoint())
    assert cfg["enabled"] is True and cfg["mode"] == "core"
    assert "www.7tan.com" in sc.get_update_endpoint()
    print("✅ 自检通过")


if __name__ == "__main__":
    main()
