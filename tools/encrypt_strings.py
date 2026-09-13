#!/usr/bin/env python3
"""
敏感字符串加密工具

使用 AES-256-GCM 加密 RSA 公钥和 API 端点 URL，
生成加密后的 base64 字符串，直接写入 strings.py。

⚠️ 仅开发者使用，运行一次后即可删除。

用法:
    python tools/encrypt_strings.py              # 交互式输入
    python tools/encrypt_strings.py --stdin      # 从 stdin 读取 JSON
    python tools/encrypt_strings.py --generate-key  # 生成新的随机密钥

输入 JSON 格式（--stdin）:
    {
        "public_key": "-----BEGIN PUBLIC KEY-----\\n...",
        "api_login": "https://7tan.com/api/auth/login.php",
        "api_verify": "https://7tan.com/api/auth/verify.php",
        "api_refresh": "https://7tan.com/api/auth/refresh.php"
    }
"""
import sys
import os
import json
import base64
import secrets
import textwrap
import re
from pathlib import Path

# 添加项目根目录到 path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ============================================================
# 配置
# ============================================================

STRINGS_PATH = ROOT / "src" / "security" / "strings.py"

# Nonce 前缀（4字节，与 strings.py 中保持一致）
NONCE_PREFIX = b'\x7f\x4a\x2e\x91'

# 当前使用的密钥（与 strings.py 同步）
_CURRENT_KEY_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'
_CURRENT_KEY_PART2 = b'\x8b\x1e\x5f\xc3\x22\xd7\x9a\x40\xee\x61\x3d\xb5\xf9\x04\x7c\xa6'

CURRENT_KEY = _CURRENT_KEY_PART1 + _CURRENT_KEY_PART2


# ============================================================
# 加密 / 解密
# ============================================================

def encrypt(plaintext: str) -> str:
    """
    使用 AES-256-GCM 加密字符串。

    格式: nonce(12字节) + ciphertext_and_tag → base64
    nonce = NONCE_PREFIX(4字节) + random(8字节)
    """
    if not plaintext:
        return ""

    # 生成随机 nonce 后 8 字节
    random_part = secrets.token_bytes(8)
    nonce = NONCE_PREFIX + random_part

    aesgcm = AESGCM(CURRENT_KEY)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    # nonce + ciphertext_with_tag → base64
    combined = nonce + ciphertext_with_tag
    return base64.b64encode(combined).decode("ascii")


def decrypt(encrypted_b64: str) -> str:
    """解密（用于验证加密结果）"""
    if not encrypted_b64:
        return ""

    try:
        raw = base64.b64decode(encrypted_b64)
    except Exception:
        return "[解码失败]"

    if len(raw) < 12:
        return "[太短]"

    nonce = raw[:12]
    ciphertext_with_tag = raw[12:]

    try:
        aesgcm = AESGCM(CURRENT_KEY)
        return aesgcm.decrypt(nonce, ciphertext_with_tag, None).decode("utf-8")
    except Exception as e:
        return f"[解密失败: {e}]"


# ============================================================
# strings.py 读写
# ============================================================

def read_strings_py() -> str:
    """读取 strings.py 完整内容"""
    if not STRINGS_PATH.exists():
        print(f"❌ 文件不存在: {STRINGS_PATH}")
        sys.exit(1)
    return STRINGS_PATH.read_text(encoding="utf-8")


def write_strings_py(content: str) -> None:
    """写入 strings.py"""
    STRINGS_PATH.write_text(content, encoding="utf-8")
    print(f"✅ 已写入: {STRINGS_PATH}")


def update_store(content: str, values: dict[str, str]) -> str:
    """
    更新 strings.py 中 _STORE 字典的值。

    使用正则替换 _STORE 字典中每个键对应的值。
    """
    for key, encrypted_value in values.items():
        if not encrypted_value:
            continue

        # 匹配 _STORE 字典中的键值对
        # 格式: "key": "old_value",
        pattern = rf'("{key}"\s*:\s*)"[^"]*"'
        replacement = rf'\1"{encrypted_value}"'

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            print(f"  ⚠️ 未找到键 '{key}' 在 _STORE 中，跳过")
        else:
            content = new_content
            print(f"  ✅ 更新: {key}")

    return content


# ============================================================
# 密钥生成
# ============================================================

def generate_new_key() -> tuple[bytes, bytes]:
    """
    生成新的随机 AES-256 密钥，分成两半。

    Returns:
        (part1, part2) 各 16 字节
    """
    key = secrets.token_bytes(32)
    part1 = key[:16]
    part2 = key[16:]
    return part1, part2


def format_key_for_code(key_bytes: bytes) -> str:
    """格式化密钥为 Python bytes 字面量"""
    hex_parts = [f"\\x{b:02x}" for b in key_bytes]
    return "b'" + "".join(hex_parts) + "'"


# ============================================================
# 交互式输入
# ============================================================

def interactive_input() -> dict[str, str]:
    """交互式输入敏感字符串"""
    print("\n" + "=" * 60)
    print(" 🔐 7Tan 敏感字符串加密工具")
    print("=" * 60)
    print()
    print("请输入需要加密的敏感字符串。")
    print("直接回车跳过（保留原值）。")
    print()

    values: dict[str, str] = {}

    # RSA 公钥
    print("─" * 60)
    print("1. RSA 公钥 (PEM 格式)")
    print("   可从 7tan.com 管理后台 → API 设置 → 公钥 获取")
    print("   粘贴时包含 -----BEGIN PUBLIC KEY----- 和 -----END PUBLIC KEY-----")
    pub_key = _multiline_input("公钥")
    if pub_key:
        values["public_key"] = encrypt(pub_key)
        print(f"   ✅ 已加密 ({len(values['public_key'])} 字符)")

    # API 端点
    print("\n─" * 60)
    print("2. API 端点 URL")

    _tan_base = __import__("os").environ.get("TANTAN_BASE_URL", "").rstrip("/")
    defaults = {
        "api_login": f"{_tan_base}/api/auth/login.php" if _tan_base else "",
        "api_verify": f"{_tan_base}/api/auth/verify.php" if _tan_base else "",
        "api_refresh": f"{_tan_base}/api/auth/refresh.php" if _tan_base else "",
        "api_trial": f"{_tan_base}/api/ai/trial.php" if _tan_base else "",
    }

    for key, default_url in defaults.items():
        label = key.replace("api_", "").title()
        url = input(f"   {label} [{default_url}]: ").strip()
        url = url or default_url
        values[key] = encrypt(url)
        print(f"   ✅ 已加密: {url}")

    return values


def _multiline_input(label: str) -> str:
    """多行输入（以空行结束）"""
    print(f"   请输入 {label}（输入空行结束）:")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines)


def stdin_input() -> dict[str, str]:
    """从 stdin 读取 JSON"""
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)

    values: dict[str, str] = {}
    for key in ["public_key", "api_login", "api_verify", "api_refresh", "api_trial"]:
        if key in data and data[key]:
            values[key] = encrypt(data[key])

    return values


# ============================================================
# 主流程
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="加密敏感字符串，写入 strings.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tools/encrypt_strings.py                  # 交互式
  python tools/encrypt_strings.py --stdin           # 从管道读取
  python tools/encrypt_strings.py --generate-key    # 生成新密钥
  echo '{"public_key":"..."}' | python tools/encrypt_strings.py --stdin
        """,
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="从 stdin 读取 JSON"
    )
    parser.add_argument(
        "--generate-key", action="store_true",
        help="生成新的随机 AES-256 密钥对"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="预览加密结果，不写入文件"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="验证 strings.py 中的加密值是否能正确解密"
    )
    args = parser.parse_args()

    # 生成密钥
    if args.generate_key:
        part1, part2 = generate_new_key()
        print("=" * 60)
        print(" 🔑 新 AES-256 密钥对")
        print("=" * 60)
        print()
        print("将以下代码替换 strings.py 中的 _KEY_PART1 和 _KEY_PART2:")
        print()
        print(f"    _KEY_PART1 = {format_key_for_code(part1)}")
        print(f"    _KEY_PART2 = {format_key_for_code(part2)}")
        print()
        print("⚠️ 更换密钥后，所有已加密值需重新生成！")
        print("   运行: python tools/encrypt_strings.py")
        return

    # 验证模式
    if args.verify:
        content = read_strings_py()
        print("🔍 验证 strings.py 加密值...\n")

        # 提取 _STORE 中的值
        store_match = re.search(
            r'_STORE:\s*dict\[str,\s*str\]\s*=\s*\{(.*?)\}',
            content, re.DOTALL
        )
        if not store_match:
            print("❌ 找不到 _STORE 字典")
            return

        store_body = store_match.group(1)
        all_ok = True

        for key in ["public_key", "api_login", "api_verify", "api_refresh", "api_trial"]:
            match = re.search(rf'"{key}"\s*:\s*"([^"]*)"', store_body)
            if match:
                encrypted = match.group(1)
                if encrypted:
                    decrypted = decrypt(encrypted)
                    if decrypted.startswith("["):
                        print(f"  ❌ {key}: {decrypted}")
                        all_ok = False
                    else:
                        # 截断显示
                        display = decrypted[:80] + "..." if len(decrypted) > 80 else decrypted
                        print(f"  ✅ {key}: {display}")
                else:
                    print(f"  ⚠️ {key}: 空值")
            else:
                print(f"  ⚠️ {key}: 未找到")

        if all_ok:
            print("\n✅ 所有值正常")
        return

    # 获取输入
    if args.stdin:
        values = stdin_input()
    else:
        values = interactive_input()

    if not values:
        print("⚠️ 没有输入任何值，退出。")
        return

    # 预览模式
    if args.dry_run:
        print("\n📋 预览加密结果:\n")
        for key, encrypted in values.items():
            print(f"  {key}: {encrypted[:60]}...")
            decrypted = decrypt(encrypted)
            if len(decrypted) > 100:
                decrypted = decrypted[:100] + "..."
            print(f"   → 解密: {decrypted}")
            print()
        return

    # 写入 strings.py
    print("\n📝 写入 strings.py...")
    content = read_strings_py()
    content = update_store(content, values)
    write_strings_py(content)

    # 验证写入
    print("\n🔍 验证写入结果...")
    for key, encrypted in values.items():
        decrypted = decrypt(encrypted)
        if decrypted.startswith("["):
            print(f"  ❌ {key}: 加密异常")
        else:
            display = decrypted[:80] + "..." if len(decrypted) > 80 else decrypted
            print(f"  ✅ {key}: {display}")

    print("\n✅ 完成！strings.py 已更新。")
    print("💡 提示: 运行 python tools/encrypt_strings.py --verify 进行最终验证")


if __name__ == "__main__":
    main()
