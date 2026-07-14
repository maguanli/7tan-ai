"""工具函数"""
import hashlib
import random
import time
from pathlib import Path
from typing import Optional
from slugify import slugify


def slugify_filename(text: str, max_length: int = 100) -> str:
    """生成文件名友好的字符串"""
    return slugify(text, max_length=max_length)


def file_md5(filepath: Path) -> str:
    """计算文件 MD5"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def human_readable_size(size_bytes: int) -> str:
    """字节转可读大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def random_delay(min_seconds: float = 1, max_seconds: float = 5):
    """随机延迟"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def ensure_dir(path: str) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
