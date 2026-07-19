"""
7Tan Video Editor（代号「青锋」）— 轻量级 AI 驱动视频剪辑器

Phase 1: 面板壳子 + 按钮接入 + editor_api 骨架
"""

from src.ui.video_editor.editor_window import VideoEditorPage
from src.ui.video_editor.editor_api import EditorAPI
from src.ui.video_editor.data_models import (
    Clip, SubtitleClip, Track, Project, ProjectData,
    RecordingConfig, ExporterConfig, CoverTemplate, Transition,
)

__all__ = [
    "VideoEditorPage",
    "EditorAPI",
    "Clip", "SubtitleClip", "Track", "Project", "ProjectData",
    "RecordingConfig", "ExporterConfig", "CoverTemplate", "Transition",
]
