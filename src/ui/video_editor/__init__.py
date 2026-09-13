"""
7Tan Video Editor（代号"青锋"）— 精简录屏工具
"""
from src.ui.video_editor.editor_window import VideoEditorPage
from src.ui.video_editor.screen_recorder import ScreenRecorder
from src.ui.video_editor.recorder_overlay import RecorderOverlay
from src.ui.video_editor.recorder_settings import RecorderSettingsDialog
from src.ui.video_editor.data_models import (
    Project, RecordingConfig,
)

__all__ = [
    "VideoEditorPage",
    "ScreenRecorder",
    "RecorderOverlay",
    "RecorderSettingsDialog",
    "Project", "RecordingConfig",
]
