"""
视频剪辑器 — 全局配置常量
"""

from pathlib import Path

# ===== 项目默认值 =====
DEFAULT_PROJECT_NAME = "未命名项目"
DEFAULT_RESOLUTION = (1920, 1080)
DEFAULT_FPS = 30
DEFAULT_DURATION = 60.0  # 默认项目时长（秒）

# ===== 播放器 =====
PLAYER_VOLUME = 80            # 默认音量 0-100
PLAYER_LOOP = False           # 默认不循环
SEEK_STEP_SMALL = 1.0         # 逐帧步长（基于30fps ≈ 0.033s，取整数便于操作）
SEEK_STEP_LARGE = 5.0         # 大跳步长（秒）
JKL_SPEED_MULTIPLIER = 2.0    # J/K/L 倍速因子

# ===== 时间轴 =====
TRACK_HEIGHT_DEFAULT = 60     # 轨道默认高度（px）
TRACK_LABEL_WIDTH = 80        # 轨道标签宽度
TIMELINE_PIXELS_PER_SECOND = 100  # 每秒钟占多少像素
TIMELINE_MIN_ZOOM = 0.1       # 最小缩放倍数
TIMELINE_MAX_ZOOM = 10.0      # 最大缩放倍数
CLIP_MIN_DURATION = 0.1       # 最短片段（秒）
IMAGE_DEFAULT_DURATION = 5.0  # 图片默认持续（秒）

# ===== 素材库 =====
MEDIA_BIN_THUMBNAIL_SIZE = 120  # 缩略图尺寸
MEDIA_BIN_SUPPORTED_VIDEO = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".wmv")
MEDIA_BIN_SUPPORTED_AUDIO = (".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4a")
MEDIA_BIN_SUPPORTED_IMAGE = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")

# ===== 导出 =====
EXPORT_PRESETS = {
    "bilibili":  {"resolution": (1920, 1080), "fps": 30, "codec": "libx264", "bitrate": "6M"},
    "douyin":    {"resolution": (720, 1280),  "fps": 30, "codec": "libx264", "bitrate": "4M"},
    "youtube":   {"resolution": (1920, 1080), "fps": 60, "codec": "libx264", "bitrate": "12M"},
    "original":  {"resolution": None,         "fps": None, "codec": "libx264", "bitrate": "auto"},
}
EXPORT_QUALITY_DEFAULT = 85  # JPEG/PNG 质量

# ===== 录屏 =====
RECORDING_DEFAULT_FPS = 30
RECORDING_DEFAULT_CODEC = "libx264"
RECORDING_DEFAULT_QUALITY = 23  # CRF
RECORDING_MIN_DISK_GB = 1       # 录屏前最小磁盘空间（GB）

# ===== AI 封面 =====
COVER_CANVAS_SIZE = (1280, 720)
COVER_HISTORY_DEPTH = 20
SD_WEBUI_URL = "http://127.0.0.1:7860"
SD_TXT2IMG_ENDPOINT = "/sdapi/v1/txt2img"

# ===== 撤销/重做 =====
UNDO_HISTORY_DEPTH = 50

# ===== 自动保存 =====
AUTOSAVE_INTERVAL_SEC = 60
MAX_RECENT_PROJECTS = 10

# ===== 路径 =====
# ffmpeg: 优先使用 imageio_ffmpeg 自带的，否则用系统 PATH
def _find_ffmpeg():
    # 1. imageio_ffmpeg 自带（最优先）
    try:
        import imageio_ffmpeg
        p = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if p.exists():
            return p
    except Exception:
        pass
    # 2. 内置 tools 目录
    _tools_ffmpeg = Path(__file__).parent.parent.parent.parent / "tools" / "ffmpeg" / "ffmpeg.exe"
    if _tools_ffmpeg.exists():
        return _tools_ffmpeg
    # 3. 常见安装位置
    for candidate in [
        Path("G:/AI_Video/ffmpeg/ffmpeg.exe"),
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("D:/ffmpeg/bin/ffmpeg.exe"),
    ]:
        if candidate.exists():
            return candidate
    # 4. 系统 PATH 搜索
    import shutil
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    # 5. 回退
    return Path("ffmpeg")

FFMPEG_PATH = _find_ffmpeg()
VLC_PATH = Path("C:/Program Files/VideoLAN/VLC")
