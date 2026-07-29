"""
Token 本地加密存储
JWT Token 使用 AES-256-GCM 加密存储在本地文件中。
加密密钥 = PBKDF2(机器标识 + 固定盐, 迭代 100000 次)

存储位置: data/auth/token.dat
"""
import base64
import hashlib
import json
import os
import platform
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC as PBKDF2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from loguru import logger


# ============================================================
# 存储路径
# ============================================================
_AUTH_DIR = Path("data/auth")
_TOKEN_FILE = _AUTH_DIR / "token.dat"


# ============================================================
# 密钥派生
# ============================================================

# 固定盐（非机密，仅用于增加暴力破解难度）
_SALT = b'\x8b\x1e\x5f\xc3\x22\xd7\x9a\x40\xee\x61\x3d\xb5\xf9\x04\x7c\xa6'

# 额外混淆：分散存储的标识片段
_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d'
_PART2 = b'\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'


def _get_machine_id() -> str:
    """获取机器标识（多来源组合）"""
    parts = [
        platform.node(),                          # 主机名
        platform.machine(),                       # 架构
        str(uuid.getnode()),                      # MAC 地址
    ]
    # 尝试获取主板序列号（Windows）
    try:
        import subprocess
        result = subprocess.run(
            ["wmic", "baseboard", "get", "serialnumber"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.stdout:
            parts.append(result.stdout.strip())
    except Exception:
        pass

    return "|".join(parts)


def _derive_key() -> bytes:
    """从机器标识派生 AES-256 密钥"""
    machine_id = _get_machine_id()
    # PBKDF2: 机器标识 + 混淆片段 → 256-bit 密钥
    material = machine_id.encode() + _PART1 + _PART2
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100_000,
        backend=default_backend(),
    )
    return kdf.derive(material)


# ============================================================
# 加密 / 解密
# ============================================================

def _encrypt(plaintext: str) -> str:
    """AES-256-GCM 加密，返回 base64 字符串"""
    key = _derive_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    raw = nonce + ciphertext
    return base64.b64encode(raw).decode("ascii")


def _decrypt(encrypted_b64: str) -> str:
    """AES-256-GCM 解密"""
    if not encrypted_b64:
        return ""
    try:
        raw = base64.b64decode(encrypted_b64)
    except Exception:
        return ""
    if len(raw) < 12:
        return ""
    nonce = raw[:12]
    ciphertext = raw[12:]
    try:
        key = _derive_key()
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception:
        return ""


# ============================================================
# 公开 API
# ============================================================

def save_token(token: str, username: str = "", level: str = "basic",
               pro_expires: int = 0, expires_in: int = 0,
               trial_ai_count: int = 0, pro_license: str = "") -> bool:
    """
    加密保存 JWT Token 到本地。

    Args:
        token: JWT Token 字符串
        username: 用户名
        level: 会员等级
        pro_expires: 专业版到期时间（Unix 时间戳）
        expires_in: Token 有效期（秒，0=使用默认30天）
        trial_ai_count: AI 试用剩余次数（0=已用完，来自服务端 JWT）

    Returns:
        是否保存成功
    """
    try:
        _AUTH_DIR.mkdir(parents=True, exist_ok=True)

        # 防御：token 必须是字符串，不能是 dict 或其他类型
        if not isinstance(token, str):
            logger.error(f"[Token] save_token 收到了非字符串 token: {type(token)}")
            return False
        if not token.strip():
            logger.error("[Token] save_token 收到了空 token")
            return False

        payload = {
            "token": token,
            "username": username,
            "level": level,
            "pro_expires": pro_expires,
            "saved_at": int(__import__("time").time()),
            "expires_in": expires_in or 2592000,  # 默认 30 天
            "trial_ai_count": trial_ai_count,
            "pro_license": pro_license or "",
        }

        encrypted = _encrypt(json.dumps(payload, ensure_ascii=False))
        _TOKEN_FILE.write_text(encrypted, encoding="utf-8")
        logger.info(f"[Token] 已保存 (用户: {username}, 等级: {level})")
        return True
    except Exception as e:
        logger.error(f"[Token] 保存失败: {e}")
        return False


def load_token() -> dict | None:
    """
    加载并解密本地 JWT Token。

    Returns:
        {
            "token": "eyJhbGci...",
            "username": "player1",
            "level": "pro",
            "pro_expires": 1735689600,
            "saved_at": 1700000000,
            "expires_in": 2592000,
        }
        如果文件不存在或解密失败返回 None
    """
    if not _TOKEN_FILE.exists():
        return None

    try:
        encrypted = _TOKEN_FILE.read_text(encoding="utf-8").strip()
        if not encrypted:
            return None
        plaintext = _decrypt(encrypted)
        if not plaintext:
            # 解密失败 — 可能是换了机器，删除无效文件
            logger.warning("[Token] 解密失败，可能已更换设备，清除旧 Token")
            _TOKEN_FILE.unlink(missing_ok=True)
            return None
        return json.loads(plaintext)
    except Exception as e:
        logger.error(f"[Token] 加载失败: {e}")
        return None


def clear_token() -> bool:
    """删除本地 Token（退出登录）"""
    try:
        _TOKEN_FILE.unlink(missing_ok=True)
        logger.info("[Token] 已清除")
        return True
    except Exception as e:
        logger.error(f"[Token] 清除失败: {e}")
        return False


def is_token_available() -> bool:
    """检查是否有可用的本地 Token"""
    data = load_token()
    if not data:
        return False
    token = data.get("token", "")
    if not token:
        return False
    # 检查是否在有效期内
    saved_at = data.get("saved_at", 0)
    expires_in = data.get("expires_in", 2592000)
    now = int(__import__("time").time())
    if now - saved_at > expires_in:
        return False
    return True
