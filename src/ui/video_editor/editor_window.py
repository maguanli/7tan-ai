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
        self._recorder.on_audio_warning = self._on_audio_warning

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
    #  UI 构建
    # ==================================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 中央区域：开始录屏按钮
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_record = QPushButton("🎥 开始录屏")
        self._btn_record.setFixedSize(280, 100)
        self._btn_record.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_record.setStyleSheet("""
            QPushButton {
                background-color: #d9534f; color: white;
                border: none; border-radius: 12px;
                padding: 20px 48px; font-size: 22px; font-weight: bold;
            }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
            QPushButton:disabled {
                background-color: #337ab7; color: white;
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
        """异步启动录制引擎 + 显示控制条

        关键设计：按钮状态在主线程立即切换，不依赖工作线程回调。
        只有录制引擎启动失败时才回退按钮状态。
        """
        # ✅ 主线程立即更新 UI（不等工作线程）
        self._btn_record.setText("🔴 正在录屏…")
        self._btn_record.setEnabled(False)
        self._status.setText("🔴 正在启动录制…")
        self._recording_timer.start()

        # 显示浮动控制条
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.activateWindow()

        def _do_start():
            try:
                ok = self._recorder.start(config)
                if ok:
                    # 成功：按钮保持「正在录屏」，更新状态文字
                    QTimer.singleShot(0, lambda: self._status.setText("🔴 正在录制…"))
                else:
                    # 失败：回退按钮 + 隐藏控制条
                    QTimer.singleShot(0, self._on_recording_start_failed)
            except Exception as e:
                logger.error(f"录制引擎启动异常: {e}")
                QTimer.singleShot(0, self._on_recording_start_failed)

        import threading
        threading.Thread(target=_do_start, daemon=True).start()

    def _on_recording_start_failed(self):
        """录制启动失败：回退所有 UI 状态"""
        self._recording_timer.stop()
        self._btn_record.setText("🎥 开始录屏")
        self._btn_record.setEnabled(True)
        self._overlay.hide()
        self._status.setText("❌ 录制启动失败")

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
    #  录制状态更新（全部线程安全）
    # ==================================================================

    def _on_recording_time(self, seconds: float):
        self._overlay.set_time(seconds)

    def _update_recording_time(self):
        if self._recorder.is_recording:
            self._overlay.set_time(self._recorder.elapsed)

    def _on_recording_state(self, state: str):
        """录制状态变化 — 线程安全：始终 marshal 到主线程更新 UI"""
        def _update():
            if state == "paused":
                self._status.setText("⏸ 录制已暂停")
            elif state == "recording":
                self._status.setText("🔴 正在录制…")
            elif state == "stopped":
                self._btn_record.setText("🎥 开始录屏")
                self._btn_record.setEnabled(True)
                self._status.setText("✅ 录制已停止")
        QTimer.singleShot(0, _update)

    def _on_recording_error(self, msg: str):
        """录制错误 — 线程安全"""
        def _update():
            self._status.setText(f"❌ 录制错误: {msg}")
            self._btn_record.setText("🎥 开始录屏")
            self._btn_record.setEnabled(True)
        QTimer.singleShot(0, _update)
        QTimer.singleShot(3000, self._overlay.hide)

    def _on_audio_warning(self, msg: str):
        """音频不可用警告 — 线程安全：状态栏提示（不再静默无声）"""
        logger.warning(f"[录屏] {msg}")

        def _update():
            self._status.setText(f"⚠️ {msg}")
        QTimer.singleShot(0, _update)
