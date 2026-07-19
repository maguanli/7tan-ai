"""
7Tan Video Editor（代号「青锋」）— 轻量级 AI 驱动视频剪辑器

Phase 2: 播放器 + 素材导入 + 时间轴显示
"""

from src.ui.video_editor.editor_window import VideoEditorPage
from src.ui.video_editor.editor_api import EditorAPI
from src.ui.video_editor.player import VideoPlayer
from src.ui.video_editor.media_bin import MediaBin
from src.ui.video_editor.timeline import TimelineView
from src.ui.video_editor.data_models import (
    Clip, SubtitleClip, Track, Project, ProjectData,
    RecordingConfig, ExporterConfig, CoverTemplate, Transition,
)

__all__ = [
    "VideoEditorPage",
    "EditorAPI",
    "VideoPlayer",
    "MediaBin",
    "TimelineView",
    "Clip", "SubtitleClip", "Track", "Project", "ProjectData",
    "RecordingConfig", "ExporterConfig", "CoverTemplate", "Transition",
]
