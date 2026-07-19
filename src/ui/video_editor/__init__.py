"""
7Tan Video Editor（代号"青锋"）— 轻量级 AI 驱动视频剪辑器

Phase 5: +AI剪辑引擎 +AI配音 +AI字幕 +封面制作
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
    "ScreenRecorder",
    "RecorderOverlay",
    "RecorderSettingsDialog",
    "AIClipEngine",
    "AIDubEngine",
    "AISubtitleEngine",
    "CoverEditor",
    "CoverAIEngine",
    "Clip", "SubtitleClip", "Track", "Project", "ProjectData",
    "RecordingConfig", "ExporterConfig", "CoverTemplate", "Transition",
]
