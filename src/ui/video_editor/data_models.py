"""
视频剪辑器 — 数据模型

所有核心数据结构定义。与架构文档第十一章一一对应。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Keyframe:
    """关键帧 — 动画插值点（参见 Phase 6）"""
    id: str
    time: float = 0.0                 # 时间位置（秒）
    property: str = "opacity"          # 动画属性: opacity / scale_x / scale_y / pos_x / pos_y / rotation
    value: float = 1.0                # 属性值
    easing: str = "linear"            # 缓动: linear / ease_in / ease_out / ease_in_out
    params: dict = field(default_factory=dict)


@dataclass
class FilterConfig:
    """滤镜配置 — 应用于单个 Clip（参见 Phase 6）"""
    id: str
    type: str = "color"               # color / blur / sharpen / vignette / lut / custom
    enabled: bool = True
    # 色彩调整
    brightness: float = 0.0           # -1.0 ~ 1.0
    contrast: float = 1.0             # 0.0 ~ 3.0
    saturation: float = 1.0           # 0.0 ~ 3.0
    hue: float = 0.0                  # 色相旋转角度
    gamma: float = 1.0                # 伽马值
    # 模糊/锐化
    blur_strength: float = 0.0        # 高斯模糊 sigma
    sharpen_strength: float = 0.0     # 锐化强度
    # 暗角
    vignette_strength: float = 0.0    # 0.0 ~ 1.0
    # LUT
    lut_path: str = ""                # 3D LUT 文件路径 (.cube)
    # 自定义 FFmpeg 滤镜字符串
    custom_filter: str = ""


@dataclass
class Clip:
    """时间轴上的一个片段

    支持 video / audio / image 三种类型。
    type="image" 的片段放在视频轨 (track_index=0)，默认持续 5 秒。
    """
    id: str
    source_path: str           # 源文件路径
    type: str                  # "video" | "audio" | "image"
    track_index: int = 0       # 所在轨道
    timeline_start: float = 0.0  # 在时间轴上的起始秒
    source_start: float = 0.0    # 裁剪起始（源文件秒数）
    source_end: float = 0.0      # 裁剪结束
    duration: float = 0.0        # 持续时长
    speed: float = 1.0           # 播放速度（1.0=正常）
    properties: dict = field(default_factory=dict)  # 音量/滤镜参数等
    filters: list = field(default_factory=list)     # list[FilterConfig] — Phase 6
    keyframes: list = field(default_factory=list)   # list[Keyframe] — Phase 6

    def __post_init__(self):
        if self.duration <= 0:
            self.duration = self.source_end - self.source_start
        if self.duration < 0:
            self.duration = 0.0
        if not isinstance(self.filters, list):
            self.filters = []
        if not isinstance(self.keyframes, list):
            self.keyframes = []

    @property
    def effective_duration(self) -> float:
        """考虑变速后的实际持续时长"""
        if self.speed and self.speed != 0:
            return self.duration / self.speed
        return self.duration


@dataclass
class SubtitleClip:
    """字幕片段（独立模型，不走 Clip）"""
    id: str
    text: str = ""                    # 字幕文本
    start_time: float = 0.0           # 开始时间（秒）
    end_time: float = 0.0             # 结束时间（秒）
    track_index: int = 0              # 所在字幕轨道
    font: str = "Microsoft YaHei"     # 字体
    font_size: int = 24               # 字号
    color: str = "#FFFFFF"            # 颜色（HEX）
    position: str = "bottom"          # 位置：bottom / top / center
    has_outline: bool = True          # 是否有描边

    @property
    def duration(self) -> float:
        return max(0, self.end_time - self.start_time)


@dataclass
class Transition:
    """转场效果 — 两个相邻片段之间的过渡"""
    id: str
    type: str = "fade"                # fade / dissolve / wipe / slide / zoom / none
    duration: float = 0.5             # 转场持续秒数
    prev_clip_id: str = ""            # 前一片段 ID
    next_clip_id: str = ""            # 后一片段 ID
    params: dict = field(default_factory=dict)  # 类型特定参数


@dataclass
class Track:
    """一个轨道。

    type="video"|"audio" → clips 存 Clip；
    type="subtitle" → clips 存 SubtitleClip。
    """
    type: str                         # "video" | "audio" | "subtitle"
    clips: list = field(default_factory=list)  # list[Clip | SubtitleClip]
    muted: bool = False
    locked: bool = False

    @property
    def total_duration(self) -> float:
        """轨道总时长（最后一个片段结束的时间）"""
        if not self.clips:
            return 0.0
        last = self.clips[-1]
        if isinstance(last, Clip):
            return last.timeline_start + last.effective_duration
        elif isinstance(last, SubtitleClip):
            return last.end_time
        return 0.0


@dataclass
class Project:
    """项目文件（运行时对象）。

    ProjectData 是其 JSON 序列化形态，二者字段一致。
    file_path 仅运行时持有，不存入 JSON。
    """
    version: str = "1.0"
    name: str = "未命名项目"
    file_path: str = ""               # .7tanproj 路径（仅运行时）
    created_at: str = ""
    modified_at: str = ""
    tracks: list = field(default_factory=list)  # list[Track]
    resolution: tuple = (1920, 1080)
    fps: int = 30
    duration: float = 0.0
    cover_data: Optional[dict] = None   # 封面图层树
    undo_stack: list = field(default_factory=list)
    transitions: list = field(default_factory=list)  # list[Transition]

    @property
    def all_clips(self) -> list:
        """获取所有轨道上的 Clip（不含 SubtitleClip）"""
        result = []
        for t in self.tracks:
            for c in t.clips:
                if isinstance(c, Clip):
                    result.append(c)
        return result

    def to_data(self) -> "ProjectData":
        """转为可持久化的 ProjectData"""
        return ProjectData(
            version=self.version,
            name=self.name,
            resolution=self.resolution,
            fps=self.fps,
            tracks=self.tracks,
            cover_data=self.cover_data,
            undo_stack=self.undo_stack,
            duration=self.duration,
            created_at=self.created_at,
            modified_at=self.modified_at,
            transitions=self.transitions,
        )


@dataclass
class ProjectData:
    """项目持久化结构 — .7tanproj JSON 格式。

    与 Project 字段一一对应。file_path 不存入 JSON。
    """
    version: str = "1.0"
    name: str = "未命名项目"
    resolution: tuple = (1920, 1080)
    fps: int = 30
    tracks: list = field(default_factory=list)
    cover_data: Optional[dict] = None
    undo_stack: list = field(default_factory=list)
    duration: float = 0.0
    created_at: str = ""
    modified_at: str = ""
    transitions: list = field(default_factory=list)  # list[Transition]

    def to_project(self, file_path: str = "") -> Project:
        """还原为运行时 Project 对象"""
        return Project(
            version=self.version,
            name=self.name,
            file_path=file_path,
            resolution=self.resolution,
            fps=self.fps,
            tracks=self.tracks,
            cover_data=self.cover_data,
            undo_stack=self.undo_stack,
            duration=self.duration,
            created_at=self.created_at,
            modified_at=self.modified_at,
            transitions=self.transitions,
        )


@dataclass
class RecordingConfig:
    """录屏配置"""
    mode: str = "fullscreen"          # "fullscreen" | "region" | "window"
    fps: int = 15  # 默认15fps，降低CPU
    codec: str = "libx264"
    quality: int = 23                 # CRF
    capture_system_audio: bool = True   # 默认开启（自动检测设备，失败则仅录画面）
    capture_mic: bool = False
    mic_volume: float = 0.8           # 0.0 ~ 1.0
    mic_device_id: Optional[int] = None  # PyAudio 设备索引
    output_dir: str = ""
    region_rect: tuple = (0, 0, 1920, 1080)  # (x, y, w, h)
    window_title: str = ""            # 窗口模式


@dataclass
class ExporterConfig:
    """导出配置（参见五-A）"""
    export_type: str = "video"        # video / cover_image / audio_only
    resolution: tuple = (1920, 1080)
    fps: int = 30
    codec: str = "libx264"            # libx264 / libx265 / vp9 / png / jpg / mp3 / wav
    bitrate: str = "6M"
    quality: int = 85                 # 封面图片质量 / 音频比特率等级
    output_format: str = "mp4"        # mp4 / mov / webm / gif / png / jpg / mp3 / wav
    preset: str = "medium"            # fast / medium / slow（仅 video）


@dataclass
class CoverTemplate:
    """封面模板（参见 9.6）"""
    name: str = ""
    style: str = ""                   # 游戏/Vlog/教程/搞笑/科技/自定义
    bg_color: str = "#1a1a2e"
    gradient: Optional[str] = None
    font: str = "Microsoft YaHei"
    title_position: tuple = (540, 200)
    subtitle_position: Optional[tuple] = None
    decor_elements: list = field(default_factory=list)


@dataclass
class SceneScript:
    """AI 视频制作 — 单个分镜头脚本（参见第十五章）"""
    index: int = 0
    text: str = ""                     # 配音文案
    image_prompt: str = ""             # AI 生图提示词（可选）
    duration: float = 10.0             # 预估时长（秒）
    transition: str = "fade"           # 转场类型
    image_path: Optional[str] = None   # 生成的图片路径
    audio_path: Optional[str] = None   # 生成的配音路径


@dataclass
class VideoScript:
    """AI 视频制作 — 完整视频脚本（参见第十五章）"""
    title: str = ""
    style: str = "professional"        # professional / casual / tech / funny
    scenes: list = field(default_factory=list)  # list[SceneScript]
    total_duration: float = 0.0


@dataclass
class AIVideoTask:
    """AI 视频制作 — 任务状态跟踪（参见第十五章）"""
    id: str = ""
    status: str = "idle"               # idle / scripting / generating_images / dubbing / arranging / done / failed
    script: Optional['VideoScript'] = None
    progress: float = 0.0              # 0.0 ~ 1.0
    message: str = ""
    created_at: str = ""
