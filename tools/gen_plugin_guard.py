#!/usr/bin/env python3
"""生成 src/security/plugin_guard.py — 注入 AES-256-GCM 加密的 HMAC 密钥

用法: python tools/gen_plugin_guard.py
    → 生成 src/security/plugin_guard.py（含加密密钥）
    → 再用 tools/compile_harden.py 编译为 .pyd（编译后 .py 移入 backups）
"""
import base64
import io
import secrets
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "security_src" / "plugin_guard.py"
OUT = ROOT / "src" / "security" / "plugin_guard.py"

# 与 gen_sec_config.py / sec_config.py 相同的密钥与 nonce 前缀
_KEY_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'
_KEY_PART2 = b'\x8b\x1e\x5f\xc3\x22\xd7\x9a\x40\xee\x61\x3d\xb5\xf9\x04\x7c\xa6'
_NONCE_PREFIX = b'\x7f\x4a\x2e\x91'
KEY = _KEY_PART1 + _KEY_PART2


def encrypt(plaintext: bytes) -> str:
    nonce = _NONCE_PREFIX + secrets.token_bytes(8)
    ct = AESGCM(KEY).encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ct).decode("ascii")


def main():
    if not TEMPLATE.exists():
        print(f"❌ 模板不存在: {TEMPLATE}")
        sys.exit(1)

    hmac_key = secrets.token_bytes(32)
    enc = encrypt(hmac_key)
    code = TEMPLATE.read_text(encoding="utf-8")
    if "__HMAC_ENC__" not in code:
        print("❌ 模板中未找到占位符 __HMAC_ENC__")
        sys.exit(1)
    code = code.replace("__HMAC_ENC__", enc)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(code, encoding="utf-8")
    print(f"✅ 已生成: {OUT}")
    print(f"   HMAC 密钥: {len(hmac_key)}B（随机生成，AES-256-GCM 加密注入）")
    print(f"   下一步: python tools/compile_harden.py 编译为 .pyd")


if __name__ == "__main__":
    main()
