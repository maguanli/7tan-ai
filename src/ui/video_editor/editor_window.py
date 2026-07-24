"""
录屏工具 — 主窗口 (VideoEditorPage)
精简版：只保留录屏功能，播放器/时间轴/制图/语音/AI 已全部移除。
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QDialog,
)
from PyQt6.QtCore import Qt, QTimer

from loguru import logger

from ..theme import THEME
from src.ui.video_editor.data_models import RecordingConfig
from src.ui.video_editor.project_manager import ProjectManager
from src.ui.video_editor.screen_recorder import ScreenRecorder
from src.ui.video_editor.recorder_overlay import RecorderOverlay
from src.ui.video_editor.recorder_settings import RecorderSettingsDialog


class VideoEditorPage(QWidget):
    """录屏工具 — 点击即可开始录制屏幕"""

    def __init__(self):
        super().__init__()
        self._pm = ProjectManager()
        self.project = self._pm.new_project()

        # 录屏引擎
        self._recorder = ScreenRecorder()
        self._recorder.on_time_updated = self._on_recording_time
        self._recorder.on_state_changed = self._on_recording_state
        self._recorder.on_error = self._on_recording_error

        # 浮动控制条
        self._overlay = RecorderOverlay()
        self._overlay.pause_clicked.connect(self._on_overlay_pause)
        self._overlay.resume_clicked.connect(self._on_overlay_resume)
        self._overlay.stop_clicked.connect(self._on_overlay_stop)
        self._overlay.overlay_closed.connect(self._on_overlay_closed)

        # 定时刷新录制时间
        self._recording_timer = QTimer(self)
        self._recording_timer.setInterval(200)
        self._recording_timer.timeout.connect(self._update_recording_time)

        self._build_ui()

        # 清理上次异常退出残留的 ffmpeg 进程
        orphan_count = ScreenRecorder.kill_orphan_ffmpeg()
        if orphan_count > 0:
            logger.info(f"启动时清理了 {orphan_count} 个孤儿录屏进程")

    # ==================================================================
    #  UI
    # ==================================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主区域：居中大按钮
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_record = QPushButton("🎥 开始录屏")
        self._btn_record.setStyleSheet("""
            QPushButton {
                background-color: #d9534f; color: white;
                border: none; border-radius: 12px;
                padding: 20px 48px; font-size: 22px; font-weight: bold;
            }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
            QPushButton:disabled {
                background-color: #5cb85c; color: white;
            }
        """)
        self._btn_record.clicked.connect(self._on_start_recording)
        cl.addWidget(self._btn_record)

        hint = QLabel("点击按钮开始录制屏幕")
        hint.setStyleSheet(
            f"color:{THEME['text_muted']}; font-size:13px; margin-top:12px;"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(hint)

        layout.addWidget(center)

        # 状态栏
        self._status = QLabel("就绪")
        self._status.setStyleSheet(
            f"color:{THEME['text_muted']}; padding:4px 8px; font-size:11px;"
        )
        layout.addWidget(self._status)

    # ==================================================================
    #  录屏流程
    # ==================================================================

    def _on_start_recording(self):
        """弹出录制设置 → 启动录制"""
        dlg = RecorderSettingsDialog(RecordingConfig(output_dir=''), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            config = dlg.get_config()
            QTimer.singleShot(100, lambda: self._start_recording_with_config(config))

    def _start_recording_with_config(self, config: RecordingConfig):
        """异步启动录制引擎 + 显示控制条"""
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.activateWindow()
        self._status.setText("🔴 正在启动录制…")
        self._recording_starting = True

        def _do_start():
            ok = self._recorder.start(config)
            if ok and self._recording_starting:
                QTimer.singleShot(0, lambda: (
                    self._btn_record.setText("🔴 正在录屏…"),
                    self._btn_record.setEnabled(False),
                    self._status.setText("🔴 正在录制…"),
                    self._recording_timer.start(),
                    setattr(self, '_recording_starting', False),
                ))
            else:
                QTimer.singleShot(0, lambda: (
                    self._btn_record.setText("🎥 开始录屏"),
                    self._btn_record.setEnabled(True),
                    self._overlay.hide(),
                    self._status.setText("❌ 录制启动失败"),
                    setattr(self, '_recording_starting', False),
                ))

        import threading
        threading.Thread(target=_do_start, daemon=True).start()

    # ==================================================================
    #  录制控制条回调
    # ==================================================================

    def _on_overlay_pause(self):
        self._recorder.pause()

    def _on_overlay_resume(self):
        self._recorder.resume()

    def _on_overlay_stop(self):
        self._recording_timer.stop()
        self._overlay.hide()
        self._btn_record.setText("🎥 开始录屏")
        self._btn_record.setEnabled(True)
        result = self._recorder.stop()
        if result:
            self._status.setText(f"✅ 录制完成: {result}")
        else:
            self._status.setText("✅ 录制已停止")

    def _on_overlay_closed(self):
        if self._recorder.is_recording:
            self._recorder.stop()

    # ==================================================================
    #  录制状态更新
    # ==================================================================

    def _on_recording_time(self, seconds: float):
        self._overlay.set_time(seconds)

    def _update_recording_time(self):
        if self._recorder.is_recording:
            self._overlay.set_time(self._recorder.elapsed)

    def _on_recording_state(self, state: str):
        if state == "paused":
            self._status.setText("⏸ 录制已暂停")
        elif state == "recording":
            self._status.setText("🔴 正在录制…")
        elif state == "stopped":
            self._btn_record.setText("🎥 开始录屏")
            self._btn_record.setEnabled(True)
            self._status.setText("✅ 录制已停止")

    def _on_recording_error(self, msg: str):
        self._status.setText(f"❌ 录制错误: {msg}")
        self._btn_record.setText("🎥 开始录屏")
        self._btn_record.setEnabled(True)
        QTimer.singleShot(3000, self._overlay.hide)
