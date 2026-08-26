"""通用工具函数"""
import hashlib
import random
import shutil
import time
from pathlib import Path
from typing import Optional

from slugify import slugify as _slugify


def slugify_filename(text: str, max_length: int = 100) -> str:
    """生成文件名友好的 URL 安全字符串"""
    return _slugify(text, max_length=max_length)


def file_md5(filepath: Path) -> str:
    """计算文件 MD5（大文件分块读取）"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def file_sha256(filepath: Path) -> str:
    """计算文件 SHA-256（大文件分块读取）"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def human_readable_size(size_bytes: int) -> str:
    """字节转可读大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def random_delay(min_seconds: float = 1, max_seconds: float = 5):
    """随机延迟"""
    time.sleep(random.uniform(min_seconds, max_seconds))


def ensure_dir(path: str) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def disk_usage_gb(path: str = ".") -> float:
    """获取磁盘剩余空间（GB）"""
    usage = shutil.disk_usage(path)
    return usage.free / (1024 ** 3)


def parse_size_to_bytes(size_str: str) -> Optional[int]:
    """解析大小字符串为字节数，如 '45.2 GB' → 45200000000"""
    if not size_str:
        return None
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    size_str = size_str.strip().upper()
    # 按单位长度降序匹配，避免 "1GB" 先被 "B" 匹配导致解析失败
    for unit, multiplier in sorted(units.items(), key=lambda kv: -len(kv[0])):
        if size_str.endswith(unit):
            try:
                return int(float(size_str.replace(unit, "").strip()) * multiplier)
            except ValueError:
                return None
    try:
        return int(float(size_str))
    except ValueError:
        return None
