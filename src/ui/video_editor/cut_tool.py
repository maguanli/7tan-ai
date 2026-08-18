"""
视频剪辑器 — 切割工具

在播放头位置切割片段。支持：
- Ctrl+K / S 键切割
- 右键菜单「在此切割」
- 批量切割（所有轨道在播放头处同时切割）

Phase 3: 基础切割功能
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.video_editor.data_models import Project, Clip

from loguru import logger

from src.ui.video_editor.data_models import Clip as ClipModel
from src.ui.video_editor.utils import generate_clip_id


class CutTool:
    """切割工具 — 对项目数据模型进行操作"""

    def __init__(self):
        self._last_cut_time: float = 0.0
        self._last_cut_count: int = 0

    # ==================================================================
    #  公开 API
    # ==================================================================

    def cut_at_playhead(self, project: "Project", playhead_time: float,
                         track_index: Optional[int] = None) -> int:
        """在播放头位置切割片段

        Args:
            project: 项目对象
            playhead_time: 播放头时间（秒）
            track_index: 指定轨道（None=切割所有轨道上位于播放头下的片段）

        Returns:
            切割产生的片段数
        """
        if not project or not project.tracks:
            return 0

        cut_count = 0
        playhead_time = max(0.001, playhead_time)  # 避免切在 0 位置

        if track_index is not None:
            # 指定轨道
            if track_index < len(project.tracks):
                if self._cut_track(project.tracks[track_index], playhead_time):
                    cut_count += 1
        else:
            # 所有轨道（仅视频轨和音频轨，字幕轨走 SubtitleClip 不走 Clip）
            for track in project.tracks:
                if track.type in ("video", "audio"):
                    if self._cut_track(track, playhead_time):
                        cut_count += 1

        if cut_count > 0:
            self._last_cut_time = playhead_time
            self._last_cut_count = cut_count
            logger.info(f"切割: {cut_count} 个片段 @ {playhead_time:.2f}s")
        else:
            logger.debug(f"切割: 播放头 {playhead_time:.2f}s 处无可切割片段")

        return cut_count

    def can_cut(self, project: "Project", playhead_time: float,
                 track_index: Optional[int] = None) -> bool:
        """检查播放头位置是否可以切割"""
        if not project or not project.tracks:
            return False

        tracks_to_check = (
            [project.tracks[track_index]] if track_index is not None and track_index < len(project.tracks)
            else [t for t in project.tracks if t.type in ("video", "audio")]
        )

        for track in tracks_to_check:
            for clip in track.clips:
                if not isinstance(clip, ClipModel):
                    continue
                if (clip.timeline_start < playhead_time <
                        clip.timeline_start + clip.effective_duration):
                    # 还要确保不在片段的边缘（太近边缘切了无意义）
                    margin = 0.05  # 50ms 边缘
                    effective_end = clip.timeline_start + clip.effective_duration
                    if (playhead_time - clip.timeline_start > margin and
                            effective_end - playhead_time > margin):
                        return True
        return False

    def cut_clip_at(self, project: "Project", track_index: int, clip_index: int,
                     cut_time: float) -> bool:
        """在指定片段的指定位置切割（相对于片段起始）

        Args:
            project: 项目对象
            track_index: 轨道索引
            clip_index: 片段在轨道中的索引
            cut_time: 切割时间（相对于片段 timeline_start 的秒数）

        Returns:
            是否成功
        """
        if track_index >= len(project.tracks):
            return False
        track = project.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clips):
            return False

        clip = track.clips[clip_index]
        if not isinstance(clip, ClipModel):
            return False

        source_cut_time = clip.source_start + cut_time / max(clip.speed, 0.01)

        if source_cut_time <= clip.source_start or source_cut_time >= clip.source_end:
            return False

        return self._split_clip(track, clip_index, clip, source_cut_time)

    # ==================================================================
    #  内部方法
    # ==================================================================

    def _cut_track(self, track, playhead_time: float) -> bool:
        """在指定轨道的播放头位置切割"""
        for i, clip in enumerate(track.clips):
            if not isinstance(clip, ClipModel):
                continue

            clip_start = clip.timeline_start
            clip_end = clip_start + clip.effective_duration

            # 播放头在这个片段内吗？
            if clip_start < playhead_time < clip_end:
                # 边缘保护
                margin = 0.05
                if (playhead_time - clip_start <= margin or
                        clip_end - playhead_time <= margin):
                    return False

                # 计算源文件中的切割位置
                elapsed = playhead_time - clip_start
                source_cut = clip.source_start + elapsed * clip.speed

                return self._split_clip(track, i, clip, source_cut)

        return False

    def _split_clip(self, track, clip_index: int, clip: ClipModel,
                     source_cut_time: float) -> bool:
        """执行切割：把一个 Clip 分成两个"""
        new_id = generate_clip_id()

        # 右侧新片段
        new_clip = ClipModel(
            id=new_id,
            source_path=clip.source_path,
            type=clip.type,
            track_index=clip.track_index,
            timeline_start=clip.timeline_start + (source_cut_time - clip.source_start) / max(clip.speed, 0.01),
            source_start=source_cut_time,
            source_end=clip.source_end,
            duration=clip.source_end - source_cut_time,
            speed=clip.speed,
        )

        # 修改原片段（左侧）
        clip.source_end = source_cut_time
        clip.duration = source_cut_time - clip.source_start

        # 插入新片段
        track.clips.insert(clip_index + 1, new_clip)

        return True

    # ==================================================================
    #  统计
    # ==================================================================

    @property
    def last_cut_info(self) -> tuple:
        """返回最后一次切割的 (时间, 片段数)"""
        return (self._last_cut_time, self._last_cut_count)
