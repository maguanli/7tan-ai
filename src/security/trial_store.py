"""
试用模式计数器
免费用户未登录时可试用 3 次。存储使用简单混淆防止一键重置。

存储位置: data/auth/trial.dat
"""
import base64
import json
import os
import struct
from pathlib import Path

from loguru import logger

# ============================================================
# 存储路径
# ============================================================
_AUTH_DIR = Path("data/auth")
_TRIAL_FILE = _AUTH_DIR / "trial.dat"

# 最大试用次数
MAX_TRIALS = 3

# 简单混淆密钥（非机密，仅防止记事本打开直接改数字）
_XOR_KEY = b'\x5a\x8f\x3c\x71\xe2\xb4\x0d\xa6\xf9\x1b\x47\xc3\x68\xde\x92\x55'


def _obfuscate(data: bytes) -> bytes:
    """XOR 混淆"""
    result = bytearray(len(data))
    for i, b in enumerate(data):
        result[i] = b ^ _XOR_KEY[i % len(_XOR_KEY)]
    return bytes(result)


def get_trials_left() -> int:
    """获取剩余试用次数"""
    if not _TRIAL_FILE.exists():
        return MAX_TRIALS

    try:
        raw = _TRIAL_FILE.read_bytes()
        if not raw:
            return MAX_TRIALS
        decoded = base64.b64decode(raw)
        deobfuscated = _obfuscate(decoded)
        data = json.loads(deobfuscated.decode("utf-8"))
        return data.get("trials_left", 0)
    except Exception:
        # 文件损坏，重置
        logger.warning("[Trial] 试用文件损坏，已重置")
        _reset_trials()
        return MAX_TRIALS


def use_trial() -> int:
    """
    消耗一次试用次数。

    Returns:
        剩余试用次数（0 = 已用完）
    """
    current = get_trials_left()
    if current <= 0:
        return 0

    new_count = current - 1
    _save_trials(new_count)
    logger.info(f"[Trial] 消耗 1 次，剩余 {new_count} 次")
    return new_count


def has_trials() -> bool:
    """是否还有试用次数"""
    return get_trials_left() > 0


def _save_trials(count: int) -> None:
    """保存试用次数"""
    try:
        _AUTH_DIR.mkdir(parents=True, exist_ok=True)
        data = json.dumps({"trials_left": count}, ensure_ascii=False)
        obfuscated = _obfuscate(data.encode("utf-8"))
        encoded = base64.b64encode(obfuscated)
        _TRIAL_FILE.write_bytes(encoded)
    except Exception as e:
        logger.error(f"[Trial] 保存失败: {e}")


def _reset_trials() -> None:
    """重置试用次数（仅用于文件损坏恢复）"""
    _save_trials(MAX_TRIALS)
