"""
视频剪辑器 — 主窗口 (VideoEditorPage)

Phase 1: 面板壳子 + 布局 + 按钮接入
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QStackedWidget,
    QSlider, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from loguru import logger

from src.ui.app import THEME
from src.ui.video_editor.data_models import Project, RecordingConfig
from src.ui.video_editor.project_manager import ProjectManager
from src.ui.video_editor.commands import UndoManager
from src.ui.video_editor.editor_api import EditorAPI
from src.ui.video_editor.styles import (
    EDITOR_BG, TIMELINE_BG, PLAYER_CONTROL_STYLESHEET,
    TOOLBAR_STYLESHEET, MEDIA_BIN_STYLESHEET,
)
from src.ui.video_editor.utils import format_time


class VideoEditorPage(QWidget):
    """视频剪辑器主面板"""

    # 信号：通知 ChatPage AI 操作结果
    ai_response = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._pm = ProjectManager()
        self._undo_manager = UndoManager()
        self._api = EditorAPI(self)
        self.project = self._pm.new_project()
        self._player_time = 0.0
        self._playing = False
        self._play_timer = QTimer()
        self._play_timer.timeout.connect(self._on_play_tick)
        self._setup_ui()

    @property
    def api(self) -> EditorAPI:
        return self._api

    # ==================================================================
    #  UI 构建
    # ==================================================================

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 主分屏：素材库 | 预览+时间轴 ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet(f"QSplitter::handle{{background:{THEME['border']};}}")

        # -- 左侧素材库 --
        self._media_bin = self._build_media_bin()
        splitter.addWidget(self._media_bin)

        # -- 右侧：预览 + 控制栏 + 时间轴 --
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)

        self._preview = self._build_preview()
        rl.addWidget(self._preview, 3)

        self._player_controls = self._build_player_controls()
        rl.addWidget(self._player_controls)

        self._timeline_widget = self._build_timeline_placeholder()
        rl.addWidget(self._timeline_widget, 2)

        splitter.addWidget(right)
        splitter.setSizes([200, 800])

        layout.addWidget(splitter)

        # ---- 底部工具栏 ----
        self._toolbar = self._build_toolbar()
        layout.addWidget(self._toolbar)

        # ---- 状态栏 ----
        self._status = QLabel("就绪 | 1920×1080 30fps | 轨道: 视频×1 音频×2 字幕×1")
        self._status.setStyleSheet(f"color:{THEME['text_muted']}; padding:4px 8px; font-size:11px;")
        layout.addWidget(self._status)

    # ---- 素材库 ----
    def _build_media_bin(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(4, 4, 4, 4)
        l.setSpacing(4)

        title = QLabel("📁 素材库")
        title.setStyleSheet(f"color:{THEME['accent']}; font-weight:bold; padding:4px;")
        l.addWidget(title)

        self._media_list = QListWidget()
        self._media_list.setStyleSheet(MEDIA_BIN_STYLESHEET)
        self._media_list.setDragEnabled(True)
        l.addWidget(self._media_list)

        btn_import = QPushButton("📥 导入素材")
        btn_import.setStyleSheet(TOOLBAR_STYLESHEET)
        btn_import.clicked.connect(self._on_import_media)
        l.addWidget(btn_import)

        return w

    # ---- 预览窗口 ----
    def _build_preview(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color:#000; border:1px solid {THEME['border']}; border-radius:4px;")
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._preview_label = QLabel("🎬 预览窗口\n1920 × 1080")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(f"color:{THEME['text_muted']}; font-size:16px; border:none;")
        l.addWidget(self._preview_label)

        self._time_display = QLabel("00:00.00 / 00:00.00")
        self._time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_display.setStyleSheet(f"color:{THEME['text_secondary']}; font-size:12px; border:none;")
        l.addWidget(self._time_display)

        return w

    # ---- 播放控制栏 ----
    def _build_player_controls(self) -> QWidget:
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(8, 2, 8, 2)
        l.setSpacing(6)

        btn_style = PLAYER_CONTROL_STYLESHEET

        self._btn_skip_prev = QPushButton("⏮")
        self._btn_skip_prev.setToolTip("上一段")
        self._btn_skip_prev.setStyleSheet(btn_style)

        self._btn_back = QPushButton("⏪")
        self._btn_back.setToolTip("后退 5 秒")
        self._btn_back.setStyleSheet(btn_style)
        self._btn_back.clicked.connect(lambda: self._player_seek(self._player_time - 5))

        self._btn_play = QPushButton("▶")
        self._btn_play.setToolTip("播放/暂停 (Space)")
        self._btn_play.setStyleSheet(btn_style + "font-size:22px;")
        self._btn_play.clicked.connect(self._on_play_pause)

        self._btn_fwd = QPushButton("⏩")
        self._btn_fwd.setToolTip("前进 5 秒")
        self._btn_fwd.setStyleSheet(btn_style)
        self._btn_fwd.clicked.connect(lambda: self._player_seek(self._player_time + 5))

        self._btn_skip_next = QPushButton("⏭")
        self._btn_skip_next.setToolTip("下一段")
        self._btn_skip_next.setStyleSheet(btn_style)

        for b in [self._btn_skip_prev, self._btn_back, self._btn_play,
                   self._btn_fwd, self._btn_skip_next]:
            l.addWidget(b)

        l.addSpacing(12)

        # 时间轴滑块
        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setStyleSheet(f"""
            QSlider::groove:horizontal{{background:{THEME['border']};height:6px;border-radius:3px;}}
            QSlider::handle:horizontal{{background:{THEME['accent']};width:14px;margin:-4px 0;border-radius:7px;}}
            QSlider::sub-page:horizontal{{background:{THEME['accent']}88;border-radius:3px;}}
        """)
        self._seek_slider.sliderMoved.connect(self._on_seek)
        l.addWidget(self._seek_slider, 1)

        # 音量
        vol_label = QLabel("🔊")
        vol_label.setStyleSheet("font-size:14px;")
        l.addWidget(vol_label)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedWidth(80)
        self._vol_slider.setStyleSheet(self._seek_slider.styleSheet())
        l.addWidget(self._vol_slider)

        return w

    # ---- 时间轴占位 ----
    def _build_timeline_placeholder(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color:{TIMELINE_BG}; border:1px solid {THEME['border']}; border-radius:4px;")
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("⏱️ 时间轴 — Phase 2 实现")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color:{THEME['text_muted']}; font-size:14px; border:none;")

        tracks_info = QLabel("🎬 视频轨  |  🎵 音频轨 1  |  🎵 音频轨 2  |  💬 字幕轨")
        tracks_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tracks_info.setStyleSheet(f"color:{THEME['text_muted']}; font-size:11px; border:none;")

        l.addWidget(label)
        l.addWidget(tracks_info)
        return w

    # ---- 底部工具栏 ----
    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color:{THEME['bg_card']}; border-top:1px solid {THEME['border']};")
        l = QHBoxLayout(w)
        l.setContentsMargins(8, 4, 8, 4)
        l.setSpacing(8)

        btns = [
            ("🎥 录屏", self._on_start_recording),
            ("🎙️ AI配音", self._on_ai_dub),
            ("📝 AI字幕", self._on_ai_subtitle),
            ("🖼️ 封面", self._on_open_cover),
            ("📤 导出", self._on_export),
        ]
        for text, handler in btns:
            btn = QPushButton(text)
            btn.setStyleSheet(TOOLBAR_STYLESHEET)
            btn.clicked.connect(handler)
            l.addWidget(btn)

        l.addStretch()
        return w

    # ==================================================================
    #  交互回调（内部模块调用入口）
    # ==================================================================

    def _media_bin_add(self, info: dict):
        """素材库添加一项"""
        item = QListWidgetItem(f"{'🎬' if info['type']=='video' else '🎵' if info['type']=='audio' else '🖼️'} {info['name']}")
        item.setData(Qt.ItemDataRole.UserRole, info)
        self._media_list.addItem(item)

    def _timeline_refresh(self):
        """时间轴刷新（Phase 2 实现）"""
        self._status.setText(
            f"项目: {self.project.name} | 1920×1080 30fps | "
            f"片段: {sum(len(t.clips) for t in self.project.tracks)}"
        )

    def _player_play(self):
        if not self._playing:
            self._playing = True
            self._btn_play.setText("⏸")
            self._play_timer.start(33)  # ~30fps

    def _player_pause(self):
        if self._playing:
            self._playing = False
            self._btn_play.setText("▶")
            self._play_timer.stop()

    def _on_play_pause(self):
        if self._playing:
            self._player_pause()
        else:
            self._player_play()

    def _on_play_tick(self):
        self._player_time += 0.033
        self._seek_slider.setValue(int(self._player_time * 10) % 1000)
        self._time_display.setText(
            f"{format_time(self._player_time)} / {format_time(self.project.duration)}"
        )

    def _player_seek(self, time_sec: float):
        self._player_time = max(0, min(time_sec, self.project.duration))
        self._seek_slider.setValue(int(self._player_time * 10) % 1000)
        self._time_display.setText(
            f"{format_time(self._player_time)} / {format_time(self.project.duration)}"
        )

    def _player_get_time(self) -> float:
        return self._player_time

    def _on_seek(self, value: int):
        self._player_time = value / 10.0
        self._time_display.setText(
            f"{format_time(self._player_time)} / {format_time(self.project.duration)}"
        )

    # ---- 录屏 ----
    def _on_start_recording(self):
        logger.info("录屏功能 — Phase 4 实现")
        self._status.setText("🎥 录屏功能将在 Phase 4 实现")

    def _start_recording(self, config: Optional[RecordingConfig] = None) -> bool:
        # Phase 4
        return False

    def _stop_recording(self) -> Optional[str]:
        # Phase 4
        return None

    # ---- AI 配音 ----
    def _on_ai_dub(self):
        logger.info("AI配音 — Phase 5 实现")
        self._status.setText("🎙️ AI配音功能将在 Phase 5 实现")

    # ---- AI 字幕 ----
    def _on_ai_subtitle(self):
        logger.info("AI字幕 — Phase 5 实现")
        self._status.setText("📝 AI字幕功能将在 Phase 5 实现")

    # ---- 封面 ----
    def _on_open_cover(self):
        logger.info("封面制作 — Phase 5 实现")
        self._status.setText("🖼️ 封面制作功能将在 Phase 5 实现")

    def _open_cover_editor(self):
        pass  # Phase 5

    def _ai_generate_cover(self, prompt: str) -> Optional[dict]:
        # Phase 5
        return None

    # ---- 导出 ----
    def _on_export(self):
        logger.info("导出 — Phase 3 实现")
        self._status.setText("📤 导出功能将在 Phase 3 实现")

    def _export_video(self, output_path: str, resolution: str,
                       fps: int, codec: str) -> bool:
        # Phase 3
        return False

    # ---- 导入 ----
    def _on_import_media(self):
        from PyQt6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(
            self, "导入素材", "",
            "媒体文件 (*.mp4 *.mov *.mkv *.avi *.mp3 *.wav *.png *.jpg *.jpeg *.gif);;所有文件 (*.*)"
        )
        for f in files:
            self._api.import_media(f)
