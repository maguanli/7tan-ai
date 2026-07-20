"""
视频剪辑器 — 工具函数
"""

import re
import os
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger


def format_time(seconds: float) -> str:
    """把秒数格式化为 HH:MM:SS.ms 或 MM:SS.ms

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串
    """
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 100)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:02d}"
    return f"{minutes:02d}:{secs:02d}.{millis:02d}"


def parse_time(time_str: str) -> Optional[float]:
    """把 HH:MM:SS.ms / MM:SS / 纯秒数 字符串解析为秒数

    Args:
        time_str: 时间字符串

    Returns:
        秒数，解析失败返回 None
    """
    time_str = time_str.strip()

    # 纯数字（秒）
    try:
        return float(time_str)
    except ValueError:
        pass

    # HH:MM:SS.ms
    m = re.match(r"^(\d+):(\d{1,2}):(\d{1,2})(?:\.(\d+))?$", time_str)
    if m:
        h, mi, s, ms = m.groups()
        result = int(h) * 3600 + int(mi) * 60 + int(s)
        if ms:
            result += float(f"0.{ms}")
        return result

    # MM:SS.ms
    m = re.match(r"^(\d{1,2}):(\d{1,2})(?:\.(\d+))?$", time_str)
    if m:
        mi, s, ms = m.groups()
        result = int(mi) * 60 + int(s)
        if ms:
            result += float(f"0.{ms}")
        return result

    return None


def get_file_md5(file_path: str, chunk_size: int = 8192) -> str:
    """计算文件 MD5

    Args:
        file_path: 文件路径
        chunk_size: 分块大小

    Returns:
        MD5 十六进制字符串
    """
    md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        logger.error(f"MD5 计算失败: {file_path} — {e}")
        return ""


def get_media_type(file_path: str) -> str:
    """根据扩展名判断媒体类型

    Returns:
        'video' / 'audio' / 'image' / 'unknown'
    """
    ext = Path(file_path).suffix.lower()
    video_exts = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".wmv", ".m4v"}
    audio_exts = {".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4a", ".wma"}
    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"}

    if ext in video_exts:
        return "video"
    if ext in audio_exts:
        return "audio"
    if ext in image_exts:
        return "image"
    return "unknown"


def get_media_duration_ffprobe(file_path: str) -> Optional[float]:
    """用 ffprobe 或 ffmpeg 获取视频/音频时长（秒）"""
    import subprocess
    import shutil as _shutil
    import re

    # 1. 优先 ffprobe
    ffprobe = None
    try:
        import imageio_ffmpeg
        _ff = Path(imageio_ffmpeg.get_ffmpeg_exe())
        _ffprobe = _ff.parent / _ff.name.replace("ffmpeg", "ffprobe")
        if _ffprobe.exists():
            ffprobe = _ffprobe
    except Exception:
        pass
    if ffprobe is None:
        _found = _shutil.which("ffprobe")
        if _found:
            ffprobe = Path(_found)

    if ffprobe and ffprobe.exists():
        try:
            result = subprocess.run(
                [str(ffprobe), "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", file_path],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass

    # 2. 用 ffmpeg 兜底（imageio_ffmpeg 没带 ffprobe）
    from src.ui.video_editor.config import FFMPEG_PATH
    if FFMPEG_PATH and FFMPEG_PATH.exists():
        try:
            result = subprocess.run(
                [str(FFMPEG_PATH), "-i", file_path],
                capture_output=True, text=True, encoding='utf-8',
                errors='replace', timeout=15,
            )
            stderr = result.stderr or ""
            # ffmpeg 输出: "Duration: 00:01:23.45"
            m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", stderr)
            if m:
                return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        except Exception as e:
            logger.warning(f"ffmpeg 获取时长失败: {e}")

    logger.warning("FFprobe/FFFmpeg 不可用，无法获取时长")
    return None


def generate_clip_id() -> str:
    """生成唯一片段 ID"""
    import uuid
    return str(uuid.uuid4())[:8]


def generate_project_id() -> str:
    """生成唯一项目 ID"""
    import uuid
    return str(uuid.uuid4())


def is_same_file(path_a: str, path_b: str) -> bool:
    """判断两个路径是否指向同一文件"""
    try:
        return os.path.normcase(os.path.abspath(path_a)) == \
               os.path.normcase(os.path.abspath(path_b))
    except Exception:
        return False


def human_readable_size(size_bytes: int) -> str:
    """字节数 → 人类可读的大小"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def estimate_export_size(duration_sec: float, bitrate_mbps: float) -> str:
    """估算导出文件大小

    Args:
        duration_sec: 时长（秒）
        bitrate_mbps: 码率（Mbps）

    Returns:
        人类可读的大小字符串
    """
    bits = duration_sec * bitrate_mbps * 1_000_000
    bytes_total = int(bits / 8)
    # 加上 10% 的容器开销
    bytes_total = int(bytes_total * 1.1)
    return human_readable_size(bytes_total)


def now_iso() -> str:
    """返回当前时间的 ISO 格式字符串"""
    return datetime.now().isoformat()
