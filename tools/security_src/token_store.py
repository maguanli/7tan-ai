"""
Token 本地加密存储
JWT Token 使用 AES-256-GCM 加密存储在本地文件中。
加密密钥 = PBKDF2(机器标识 + 固定盐, 迭代 100000 次)

存储位置: data/auth/token.dat

v2: level 字段加 HMAC-SHA256 防篡改。
v3: 旧版 Token 自动修复 — 无 _hmac 字段时不降级，自动补充 HMAC。
v4: 指纹稳定性修复（针对性解决"每次重启都要重新登录"）—
    ① wmic 超时 5s → 30s + 重试：冷启动 WMI 服务未就绪时不再漏读主板序列号
    ② 新增"上一次可用指纹"缓存 data/auth/.fp_cache：指纹漂移时用缓存回退
    ③ 解密失败不再删除 token.dat：避免一次冷启动抖动造成登录态永久丢失
    ④ 解密时遍历候选指纹（当前 + 缓存），任一可用即成功
    ⑤ 加密/HMAC 一律使用"最完整"的候选指纹，保证与旧数据兼容
"""
import base64
import hashlib
import hmac as _hmac_mod
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
_FPCACHE_FILE = _AUTH_DIR / ".fp_cache"   # v4: 上一次可用指纹


# ============================================================
# 常量（⚠️ 不可更改，改了旧 Token 会全部失效）
# ============================================================
_SALT = b'\x8b\x1e\x5f\xc3\x22\xd7\x9a\x40\xee\x61\x3d\xb5\xf9\x04\x7c\xa6'
_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d'
_PART2 = b'\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'
_HMAC_SALT = b'\x9d\x4e\x1a\x7f\x33\xc8\xb5\x02\xe6\xf1\x44\xd9\x0b\x56\xa8\xc3'


# ============================================================
# 机器指纹
# ============================================================

def _query_baseboard_stdout() -> str:
    """执行 wmic 取主板序列号原始 stdout。

    与旧实现保持完全一致的"口径"：返回 result.stdout 原文，
    由调用方做 .strip() —— 保证同一台机器算出的指纹与旧版逐字节相同，
    历史 Token 不会因为升级而失效。
    """
    if os.name != "nt":
        return ""
    import subprocess
    for _ in range(3):                       # v4: 重试 3 次
        try:
            result = subprocess.run(
                ["wmic", "baseboard", "get", "serialnumber"],
                capture_output=True, text=True,
                timeout=30,                  # v4: 5s → 30s（冷启动 WMI 慢）
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.stdout:
                return result.stdout
        except Exception:
            pass
    return ""


def _raw_machine_id() -> str:
    """按旧版口径计算当前指纹。"""
    parts = [
        platform.node(),                          # 主机名
        platform.machine(),                       # 架构
        str(uuid.getnode()),                      # MAC 地址
    ]
    stdout = _query_baseboard_stdout()
    if stdout:                                    # 旧版：仅在有输出时才追加
        parts.append(stdout.strip())
    return "|".join(parts)


def _read_fp_cache() -> str:
    """读取上一次成功使用的指纹（v4）"""
    try:
        if _FPCACHE_FILE.exists():
            return _FPCACHE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def _write_fp_cache(mid: str) -> None:
    """记录本次成功使用的指纹（v4）"""
    try:
        if not mid:
            return
        _AUTH_DIR.mkdir(parents=True, exist_ok=True)
        _FPCACHE_FILE.write_text(mid, encoding="utf-8")
    except Exception:
        pass


def _candidate_machine_ids() -> list:
    """候选指纹列表：当前计算值 + 缓存值（去重）"""
    out = []
    cur = _raw_machine_id()
    if cur:
        out.append(cur)
    cached = _read_fp_cache()
    if cached and cached not in out:
        out.append(cached)
    if not out:
        out.append("")
    return out


def _best_machine_id() -> str:
    """选出"最完整"的指纹（末段主板序列号非空者优先）用于加密/HMAC。"""
    cands = _candidate_machine_ids()
    for c in cands:
        _parts = c.split("|")
        if _parts[len(_parts) - 1].strip():
            return c
    return cands[0]


def _get_machine_id() -> str:
    """向后兼容别名"""
    return _best_machine_id()


# ============================================================
# 密钥派生
# ============================================================

def _derive_key_with(mid: str) -> bytes:
    """从指定机器标识派生 AES-256 密钥"""
    material = mid.encode() + _PART1 + _PART2
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100_000,
        backend=default_backend(),
    )
    return kdf.derive(material)


def _derive_hmac_key_with(mid: str) -> bytes:
    """从指定机器标识派生 HMAC 密钥（独立于加密密钥）"""
    material = mid.encode() + _HMAC_SALT
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

def _encrypt(plaintext: str, mid: str = "") -> str:
    """AES-256-GCM 加密，返回 base64 字符串"""
    mid = mid or _best_machine_id()
    key = _derive_key_with(mid)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def _decrypt_any(encrypted_b64: str):
    """遍历候选指纹尝试解密。成功返回 (plaintext, mid)，失败返回 ("", "")。"""
    if not encrypted_b64:
        return "", ""
    try:
        raw = base64.b64decode(encrypted_b64)
    except Exception:
        return "", ""
    if len(raw) < 12:
        return "", ""
    nonce = raw[:12]
    ciphertext = raw[12:]
    for mid in _candidate_machine_ids():
        try:
            aesgcm = AESGCM(_derive_key_with(mid))
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8"), mid
        except Exception:
            continue
    return "", ""


# ============================================================
# HMAC 防篡改
# ============================================================

def _compute_hmac(level: str, pro_expires: int, pro_license: str, mid: str) -> str:
    """计算敏感字段的 HMAC-SHA256"""
    hmac_key = _derive_hmac_key_with(mid)
    data = f"{level}|{pro_expires}|{pro_license}".encode("utf-8")
    digest = _hmac_mod.new(hmac_key, data, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _verify_hmac(payload: dict, mid_used: str = "") -> bool:
    """验证 HMAC，检测篡改。遍历候选指纹，任一匹配即通过。"""
    stored_hmac = payload.pop("_hmac", "")
    if not stored_hmac:
        return False

    level = payload.get("level", "free")
    pro_expires = payload.get("pro_expires", 0)
    pro_license = payload.get("pro_license", "")

    mids = [mid_used] + [c for c in _candidate_machine_ids() if c != mid_used]
    for mid in mids:
        expected = _compute_hmac(level, pro_expires, pro_license, mid)
        if _hmac_mod.compare_digest(expected.encode(), stored_hmac.encode()):
            return True
    return False


# ============================================================
# 公开 API
# ============================================================

def save_token(token: str, username: str = "", level: str = "free",
               pro_expires: int = 0, expires_in: int = 0,
               trial_ai_count: int = 0, pro_license: str = "") -> bool:
    """
    加密保存 JWT Token 到本地。

    Returns:
        是否保存成功
    """
    try:
        _AUTH_DIR.mkdir(parents=True, exist_ok=True)

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

        mid = _best_machine_id()
        payload["_hmac"] = _compute_hmac(level, pro_expires, pro_license or "", mid)

        encrypted = _encrypt(json.dumps(payload, ensure_ascii=False), mid)
        _TOKEN_FILE.write_text(encrypted, encoding="utf-8")
        _write_fp_cache(mid)
        logger.info(f"[Token] 已保存 (用户: {username}, 等级: {level})")
        return True
    except Exception as e:
        logger.error(f"[Token] 保存失败: {e}")
        return False


def load_token() -> dict | None:
    """
    加载并解密本地 JWT Token。

    - 新版 Token（含 _hmac）：验证 HMAC，失败则降级为 free
    - 旧版 Token（无 _hmac）：信任原数据，自动补充 HMAC 后重新保存
    - 解密失败：v4 起 **不再删除文件**，保留以便下次指纹恢复后自动解密

    Returns:
        dict 或 None（文件不存在 / 无法解密）
    """
    if not _TOKEN_FILE.exists():
        return None

    try:
        encrypted = _TOKEN_FILE.read_text(encoding="utf-8").strip()
        if not encrypted:
            return None

        plaintext, mid_used = _decrypt_any(encrypted)
        if not plaintext:
            # v4: 只警告，不删除 —— 冷启动指纹抖动时可自动恢复
            logger.warning("[Token] 解密失败（指纹暂不可用）。已保留本地 Token，稍后会自动恢复。")
            return None

        # 解密成功 → 记录本次可用指纹
        _write_fp_cache(mid_used)

        payload = json.loads(plaintext)

        # ── HMAC 防篡改验证 ──
        if "_hmac" in payload:
            hmac_ok = _verify_hmac(payload, mid_used)
            payload["_hmac_ok"] = hmac_ok

            if not hmac_ok:
                logger.warning(
                    "[Token] ⚠️ HMAC 验证失败！level 字段可能被篡改，降级为 free。"
                    f" 原始 level={payload.get('level')}"
                )
                payload["level"] = "free"
                payload["pro_expires"] = 0
                payload["pro_license"] = ""
        else:
            # 旧版 Token（无 HMAC）→ 信任原数据，自动补充 HMAC
            logger.info("[Token] 🔧 旧版 Token 无 HMAC 签名，自动修复...")
            payload["_hmac_ok"] = True
            try:
                save_token(
                    token=payload.get("token", ""),
                    username=payload.get("username", ""),
                    level=payload.get("level", "free"),
                    pro_expires=payload.get("pro_expires", 0),
                    expires_in=payload.get("expires_in", 0),
                    trial_ai_count=payload.get("trial_ai_count", 0),
                    pro_license=payload.get("pro_license", ""),
                )
            except Exception:
                pass  # 自动修复失败不影响加载

        return payload
    except Exception as e:
        logger.error(f"[Token] 加载失败: {e}")
        return None


def clear_token() -> bool:
    """删除本地 Token"""
    try:
        _TOKEN_FILE.unlink(missing_ok=True)
        logger.info("[Token] 已清除")
        return True
    except Exception as e:
        logger.error(f"[Token] 清除失败: {e}")
        return False


def is_token_available() -> bool:
    """
    检查本地是否有可用的 Token。
    - 文件存在、能解密、token 非空
    - 且未超过 saves_at + expires_in 有效期
    """
    data = load_token()
    if data is None:
        return False
    token = data.get("token", "")
    if not token or not token.strip():
        return False
    import time
    saved_at = data.get("saved_at", 0)
    expires_in = data.get("expires_in", 2592000)
    if saved_at + expires_in < int(time.time()):
        return False
    return True
