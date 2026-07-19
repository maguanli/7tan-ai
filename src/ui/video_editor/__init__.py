"""
7Tan Video Editor（代号"青锋"）— 轻量级 AI 驱动视频剪辑器

Phase 6: +调色滤镜 +转场 +关键帧动画 +项目保存/加载
"""

from src.ui.video_editor.editor_window import VideoEditorPage
from src.ui.video_editor.editor_api import EditorAPI
from src.ui.video_editor.player import VideoPlayer
from src.ui.video_editor.media_bin import MediaBin
from src.ui.video_editor.timeline import TimelineView
from src.ui.video_editor.screen_recorder import ScreenRecorder
from src.ui.video_editor.recorder_overlay import RecorderOverlay
from src.ui.video_editor.recorder_settings import RecorderSettingsDialog
from src.ui.video_editor.ai_clip_engine import AIClipEngine
from src.ui.video_editor.ai_dub_engine import AIDubEngine
from src.ui.video_editor.ai_subtitle_engine import AISubtitleEngine
from src.ui.video_editor.cover_editor import CoverEditor
from src.ui.video_editor.cover_ai_engine import CoverAIEngine
from src.ui.video_editor.color_filter import ColorFilterEngine
from src.ui.video_editor.transition_engine import TransitionEngine, ALL_TRANSITIONS
from src.ui.video_editor.keyframe import KeyframeManager
from src.ui.video_editor.filter_panel import FilterPanel
from src.ui.video_editor.keyframe_panel import KeyframePanel
from src.ui.video_editor.data_models import (
    Clip, SubtitleClip, Track, Project, ProjectData,
    RecordingConfig, ExporterConfig, CoverTemplate, Transition,
    FilterConfig, Keyframe,
)

__all__ = [
    "VideoEditorPage",
    "EditorAPI",
    "VideoPlayer",
    "MediaBin",
    "TimelineView",
    "ScreenRecorder",
    "RecorderOverlay",
    "RecorderSettingsDialog",
    "AIClipEngine",
    "AIDubEngine",
    "AISubtitleEngine",
    "CoverEditor",
    "CoverAIEngine",
    "ColorFilterEngine",
    "TransitionEngine", "ALL_TRANSITIONS",
    "KeyframeManager",
    "FilterPanel",
    "KeyframePanel",
    "Clip", "SubtitleClip", "Track", "Project", "ProjectData",
    "RecordingConfig", "ExporterConfig", "CoverTemplate", "Transition",
    "FilterConfig", "Keyframe",
]
