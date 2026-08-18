"""
视频剪辑器 — 转场引擎 (Phase 6)

基于 FFmpeg xfade / acrossfade 实现片段间的过渡效果。

支持的转场类型（FFmpeg xfade）:
- fade / fadeblack / fadewhite — 淡入淡出
- dissolve — 溶解
- wipeleft / wiperight / wipeup / wipedown — 擦除
- slideleft / slideright / slideup / slidedown — 滑动
- circlecrop / rectcrop — 形状裁剪
- smoothleft / smoothright / smoothup / smoothdown — 平滑过渡
- distance — 距离过渡
- hlslice / hrslice / vuslice / vdslice — 切片

音频转场用 acrossfade。
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

from src.ui.video_editor.data_models import Transition, Clip, Track


# ==================================================================
#  转场类型定义
# ==================================================================

class TransitionCategory(Enum):
    DISSOLVE = "溶解/淡入淡出"
    WIPE = "擦除"
    SLIDE = "滑动"
    SHAPE = "形状"
    SMOOTH = "平滑"
    SLICE = "切片"
    OTHER = "其他"


@dataclass
class TransitionDef:
    """转场类型定义"""
    ffmpeg_name: str          # FFmpeg xfade 名称
    display_name: str         # 中文显示名
    category: TransitionCategory
    has_audio: bool = True    # 是否有对应音频转场
    min_duration: float = 0.1
    max_duration: float = 5.0
    default_duration: float = 0.5
    params: dict = None       # 额外参数说明

    def __post_init__(self):
        if self.params is None:
            self.params = {}


# 所有可用转场
ALL_TRANSITIONS: dict[str, TransitionDef] = {
    "fade":       TransitionDef("fade", "淡入淡出", TransitionCategory.DISSOLVE),
    "fadeblack":  TransitionDef("fadeblack", "黑场淡出", TransitionCategory.DISSOLVE),
    "fadewhite":  TransitionDef("fadewhite", "白场淡出", TransitionCategory.DISSOLVE),
    "dissolve":   TransitionDef("dissolve", "溶解", TransitionCategory.DISSOLVE),
    "wiperight":  TransitionDef("wiperight", "向右擦除", TransitionCategory.WIPE),
    "wipeleft":   TransitionDef("wipeleft", "向左擦除", TransitionCategory.WIPE),
    "wipeup":     TransitionDef("wipeup", "向上擦除", TransitionCategory.WIPE),
    "wipedown":   TransitionDef("wipedown", "向下擦除", TransitionCategory.WIPE),
    "slideright": TransitionDef("slideright", "向右滑动", TransitionCategory.SLIDE),
    "slideleft":  TransitionDef("slideleft", "向左滑动", TransitionCategory.SLIDE),
    "slideup":    TransitionDef("slideup", "向上滑动", TransitionCategory.SLIDE),
    "slidedown":  TransitionDef("slidedown", "向下滑动", TransitionCategory.SLIDE),
    "circlecrop": TransitionDef("circlecrop", "圆形裁剪", TransitionCategory.SHAPE),
    "rectcrop":   TransitionDef("rectcrop", "矩形裁剪", TransitionCategory.SHAPE),
    "smoothleft": TransitionDef("smoothleft", "左平滑", TransitionCategory.SMOOTH),
    "smoothright":TransitionDef("smoothright", "右平滑", TransitionCategory.SMOOTH),
    "smoothup":   TransitionDef("smoothup", "上平滑", TransitionCategory.SMOOTH),
    "smoothdown": TransitionDef("smoothdown", "下平滑", TransitionCategory.SMOOTH),
    "distance":   TransitionDef("distance", "距离过渡", TransitionCategory.OTHER),
    "hlslice":    TransitionDef("hlslice", "水平左切片", TransitionCategory.SLICE),
    "hrslice":    TransitionDef("hrslice", "水平右切片", TransitionCategory.SLICE),
    "vuslice":    TransitionDef("vuslice", "垂直上切片", TransitionCategory.SLICE),
    "vdslice":    TransitionDef("vdslice", "垂直下切片", TransitionCategory.SLICE),
}


# ==================================================================
#  转场引擎
# ==================================================================

class TransitionEngine:
    """转场引擎"""

    @staticmethod
    def get_transition_def(trans_type: str) -> Optional[TransitionDef]:
        """获取转场类型定义"""
        return ALL_TRANSITIONS.get(trans_type)

    @staticmethod
    def get_transitions_by_category() -> dict[str, list[tuple[str, str]]]:
        """按分类获取所有转场"""
        cats: dict[str, list[tuple[str, str]]] = {}
        for key, td in ALL_TRANSITIONS.items():
            cat_name = td.category.value
            cats.setdefault(cat_name, []).append((key, td.display_name))
        return cats

    @staticmethod
    def build_xfade(prev_label: str, next_label: str,
                     trans: Transition, output_label: str = "xfade_out") -> str:
        """为两个视频片段生成 xfade FFmpeg 滤镜字符串

        Args:
            prev_label: 前一片段的标签 (如 v0)
            next_label: 后一片段的标签 (如 v1)
            trans: 转场对象
            output_label: 输出标签

        Returns:
            FFmpeg 滤镜片段，如:
            [v0][v1]xfade=transition=fade:duration=0.5:offset=1.5[xfade_out]
        """
        td = ALL_TRANSITIONS.get(trans.type)
        ffmpeg_name = td.ffmpeg_name if td else "fade"
        duration = trans.duration
        # offset: 前一 clip 结束前 duration 秒开始转场
        # offset 由调用者根据实际片段长度计算

        return (
            f"[{prev_label}][{next_label}]xfade=transition={ffmpeg_name}:"
            f"duration={duration}"
            f"[{output_label}]"
        )

    @staticmethod
    def build_xfade_with_offset(prev_label: str, next_label: str,
                                 trans: Transition, offset: float,
                                 output_label: str = "xfade_out") -> str:
        """带 offset 的 xfade

        Args:
            offset: 转场开始时间点（相对于前一片段）
        """
        td = ALL_TRANSITIONS.get(trans.type)
        ffmpeg_name = td.ffmpeg_name if td else "fade"
        duration = trans.duration

        return (
            f"[{prev_label}][{next_label}]xfade=transition={ffmpeg_name}:"
            f"duration={duration}:offset={offset}"
            f"[{output_label}]"
        )

    @staticmethod
    def build_acrossfade(prev_label: str, next_label: str,
                          duration: float, output_label: str = "afade_out") -> str:
        """为两个音频片段生成 acrossfade

        Args:
            prev_label: 前一片段的标签 (如 a0)
            next_label: 后一片段的标签 (如 a1)
            duration: 交叉淡入淡出时长
            output_label: 输出标签

        Returns:
            FFmpeg 滤镜片段
        """
        return (
            f"[{prev_label}][{next_label}]acrossfade=d={duration}:c1=tri:c2=tri"
            f"[{output_label}]"
        )

    @staticmethod
    def get_clip_pairs_for_transitions(tracks: list[Track]) -> list[tuple[Clip, Clip, int]]:
        """获取轨道上相邻的视频片段对（用于生成转场）

        Returns:
            [(prev_clip, next_clip, track_index), ...]
        """
        pairs = []
        for ti, track in enumerate(tracks):
            if track.type == "video":
                clips = [c for c in track.clips if isinstance(c, Clip)]
                for i in range(len(clips) - 1):
                    pairs.append((clips[i], clips[i + 1], ti))
        return pairs

    @staticmethod
    def find_transition(project_transitions: list[Transition],
                         prev_clip_id: str, next_clip_id: str) -> Optional[Transition]:
        """查找两个片段之间的转场"""
        for t in project_transitions:
            if t.prev_clip_id == prev_clip_id and t.next_clip_id == next_clip_id:
                return t
        return None

    @staticmethod
    def create_transition(prev_clip_id: str, next_clip_id: str,
                           trans_type: str = "fade",
                           duration: float = 0.5) -> Transition:
        """创建转场对象"""
        import uuid
        return Transition(
            id=str(uuid.uuid4())[:8],
            type=trans_type,
            duration=duration,
            prev_clip_id=prev_clip_id,
            next_clip_id=next_clip_id,
        )

    @staticmethod
    def apply_transition(project, prev_clip_id: str, next_clip_id: str,
                          trans_type: str, duration: float = 0.5):
        """向项目添加/更新转场

        Args:
            project: Project 对象
            prev_clip_id / next_clip_id: 相邻片段
            trans_type: 转场类型
            duration: 持续秒数
        """
        if not hasattr(project, 'transitions') or project.transitions is None:
            project.transitions = []

        # 查找已有
        existing = TransitionEngine.find_transition(
            project.transitions, prev_clip_id, next_clip_id
        )
        if existing:
            existing.type = trans_type
            existing.duration = duration
        else:
            t = TransitionEngine.create_transition(
                prev_clip_id, next_clip_id, trans_type, duration
            )
            project.transitions.append(t)
