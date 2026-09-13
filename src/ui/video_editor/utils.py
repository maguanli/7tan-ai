"""
视频剪辑器 — 工具函数
"""

import re
import os
import hashlib
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger


def now_iso() -> str:
    """返回当前时间的 ISO 格式字符串"""
    return datetime.now().isoformat()


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


def _parse_duration_from_ffmpeg_stderr(stderr: str) -> Optional[float]:
    """从 ffmpeg stderr 中解析时长"""
    # 方式1: "Duration: 00:01:23.45"
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", stderr)
    if m:
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        if dur > 0:
            return dur
    # 方式2: "time=00:01:23.45"（处理到末尾的时间戳）
    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", stderr)
    if times:
        h, mi, s = times[-1]
        dur = int(h) * 3600 + int(mi) * 60 + float(s)
        if dur > 0:
            return dur
    return None


def get_media_duration_ffprobe(file_path: str) -> Optional[float]:
    """用 ffprobe 或 ffmpeg 获取视频/音频时长（秒）

    三级回退策略：
      1. ffprobe（imageio_ffmpeg 自带或系统 PATH）
      2. ffmpeg -i 解析 stderr
      3. 返回 None，由调用方用 VLC 兜底
    """
    import subprocess
    import shutil as _shutil

    # ================================================================
    #  第 1 级：ffprobe
    # ================================================================
    ffprobe_paths = []

    # 1a. imageio_ffmpeg 自带的 ffprobe
    try:
        import imageio_ffmpeg
        _ff = Path(imageio_ffmpeg.get_ffmpeg_exe())
        _ffprobe = _ff.parent / _ff.name.replace("ffmpeg", "ffprobe")
        if _ffprobe.exists():
            ffprobe_paths.append(_ffprobe)
        # 有些版本 ffprobe 和 ffmpeg 是同一个文件（软链接），也试试 ffmpeg
        if _ff.exists():
            ffprobe_paths.append(_ff)
    except Exception:
        pass

    # 1b. 系统 PATH
    for name in ("ffprobe", "ffprobe.exe"):
        found = _shutil.which(name)
        if found:
            ffprobe_paths.append(Path(found))
            break

    # 1c. config 中的 FFMPEG_PATH 目录下找 ffprobe
    try:
        from src.ui.video_editor.config import FFMPEG_PATH
        if FFMPEG_PATH and FFMPEG_PATH.exists():
            ffprobe_dir = FFMPEG_PATH.parent
            ffprobe_candidate = ffprobe_dir / "ffprobe.exe"
            if ffprobe_candidate.exists():
                ffprobe_paths.append(ffprobe_candidate)
    except Exception:
        pass

    for ffprobe in ffprobe_paths:
        try:
            logger.debug(f"尝试 ffprobe: {ffprobe}")
            result = subprocess.run(
                [str(ffprobe), "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", file_path],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                dur = float(result.stdout.strip())
                if dur > 0:
                    logger.info(f"ffprobe 获取时长: {dur:.1f}s ({ffprobe})")
                    return dur
        except Exception as e:
            logger.debug(f"ffprobe 失败 ({ffprobe}): {e}")

    # ================================================================
    #  第 2 级：ffmpeg -i 解析 Duration
    # ================================================================
    ffmpeg_paths = []
    # 2a. imageio_ffmpeg
    try:
        import imageio_ffmpeg
        _ff = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if _ff.exists():
            ffmpeg_paths.append(_ff)
    except Exception:
        pass
    # 2b. config
    try:
        from src.ui.video_editor.config import FFMPEG_PATH
        if FFMPEG_PATH and FFMPEG_PATH.exists():
            ffmpeg_paths.append(FFMPEG_PATH)
    except Exception:
        pass
    # 2c. PATH
    found = _shutil.which("ffmpeg")
    if found:
        ffmpeg_paths.append(Path(found))

    for ffmpeg in ffmpeg_paths:
        try:
            logger.debug(f"尝试 ffmpeg: {ffmpeg}")
            result = subprocess.run(
                [str(ffmpeg), "-i", file_path],
                capture_output=True, text=True, encoding='utf-8',
                errors='replace', timeout=30,
            )
            stderr = result.stderr or ""
            dur = _parse_duration_from_ffmpeg_stderr(stderr)
            if dur:
                logger.info(f"ffmpeg 解析时长: {dur:.1f}s ({ffmpeg})")
                return dur
        except subprocess.TimeoutExpired:
            logger.warning(f"ffmpeg 超时 ({ffmpeg})")
        except Exception as e:
            logger.warning(f"ffmpeg 失败 ({ffmpeg}): {e}")

    # ================================================================
    #  第 3 级：文件大小估算（最后兜底）
    # ================================================================
    try:
        size_bytes = os.path.getsize(file_path)
        # 假设 2 Mbps 平均码率
        estimated = size_bytes * 8 / (2_000_000)
        if estimated > 0.5:
            logger.info(f"文件大小估算时长: {estimated:.1f}s (size={size_bytes})")
            return estimated
    except Exception:
        pass

    logger.warning(f"所有方式均无法获取时长: {file_path}")
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
        人类可读的大小
    """
    bits = duration_sec * bitrate_mbps * 1_000_000
    return human_readable_size(int(bits / 8))
