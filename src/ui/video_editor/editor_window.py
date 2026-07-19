"""
视频剪辑器 — 主窗口 (VideoEditorPage)

Phase 3: +切割 +拖拽排列 +基础导出(H.264 MP4)
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QPushButton, QSlider, QFrame, QFileDialog, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from loguru import logger

from src.ui.app import THEME
from src.ui.video_editor.data_models import Project, RecordingConfig, Track, Clip, ExporterConfig
from src.ui.video_editor.project_manager import ProjectManager
from src.ui.video_editor.commands import UndoManager
from src.ui.video_editor.editor_api import EditorAPI
from src.ui.video_editor.player import VideoPlayer
from src.ui.video_editor.media_bin import MediaBin
from src.ui.video_editor.timeline import TimelineView
from src.ui.video_editor.cut_tool import CutTool
from src.ui.video_editor.exporter import Exporter
from src.ui.video_editor.styles import (
    EDITOR_BG, TIMELINE_BG, PLAYER_CONTROL_STYLESHEET,
    TOOLBAR_STYLESHEET, MEDIA_BIN_STYLESHEET,
)
from src.ui.video_editor.utils import format_time, generate_clip_id


class VideoEditorPage(QWidget):
    """视频剪辑器主面板

    Phase 2 布局:
    ┌──────────┬──────────────────────┐
    │ 📁 素材库 │   🎬 播放器 (VLC)     │
    │ (MediaBin)│   + 控制栏            │
    ├──────────┴──────────────────────┤
    │   ⏱️ 时间轴 (TimelineView)     │
    ├─────────────────────────────────┤
    │ 🎥录屏│🎙️配音│📝字幕│🖼️封面│📤导出│
    └─────────────────────────────────┘
    """

    # 信号：通知 ChatPage AI 操作结果
    ai_response = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._pm = ProjectManager()
        self._undo_manager = UndoManager()
        self._api = EditorAPI(self)
self.project = self._pm.new_project()
        self._playing = False
        self._cut_tool = CutTool()
        self._exporter = Exporter()
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

        # ---- 主分屏：素材库 | 播放器 ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet(
            f"QSplitter::handle{{background:{THEME['border']};}}"
        )

        # -- 左侧：素材库 --
        self.media_bin = MediaBin()
        self.media_bin.media_double_clicked.connect(self._on_media_to_timeline)
        self.media_bin.media_selected.connect(self._on_media_selected)
        splitter.addWidget(self.media_bin)

        # -- 右侧：播放器 + 控制栏 --
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)

        # 播放器
        self.player = VideoPlayer()
        self.player.time_changed.connect(self._on_player_time_changed)
        self.player.state_changed.connect(self._on_player_state_changed)
        self.player.media_loaded.connect(self._on_player_media_loaded)
        rl.addWidget(self.player, 3)

        # 播放控制栏
        self._player_controls = self._build_player_controls()
        rl.addWidget(self._player_controls)

        splitter.addWidget(right)
        splitter.setSizes([220, 780])

        layout.addWidget(splitter)

        # ---- 时间轴 ----
        self.timeline = TimelineView()
        self.timeline.playhead_moved.connect(self._on_timeline_playhead_moved)
        self.timeline.clip_selected.connect(self._on_timeline_clip_selected)
self.timeline.clip_added_to_timeline.connect(self._on_timeline_clip_added)
        self.timeline.cut_requested.connect(self._on_cut)
        self.timeline.delete_requested.connect(self._on_delete_clip)
        layout.addWidget(self.timeline, 2)

        # ---- 底部工具栏 ----
        self._toolbar = self._build_toolbar()
        layout.addWidget(self._toolbar)

        # ---- 状态栏 ----
        self._status = QLabel(
            "就绪 | 1920×1080 30fps | 轨道: 🎬视频 🎵音频×2 💬字幕"
        )
        self._status.setStyleSheet(
            f"color:{THEME['text_muted']}; padding:4px 8px; font-size:11px;"
        )
        layout.addWidget(self._status)

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
        self._btn_back.clicked.connect(lambda: self._seek_relative(-5))

        self._btn_play = QPushButton("▶")
        self._btn_play.setToolTip("播放/暂停 (Space)")
        self._btn_play.setStyleSheet(btn_style + "font-size:22px;")
        self._btn_play.clicked.connect(self._on_play_pause)

        self._btn_fwd = QPushButton("⏩")
        self._btn_fwd.setToolTip("前进 5 秒")
        self._btn_fwd.setStyleSheet(btn_style)
        self._btn_fwd.clicked.connect(lambda: self._seek_relative(5))

        self._btn_skip_next = QPushButton("⏭")
        self._btn_skip_next.setToolTip("下一段")
        self._btn_skip_next.setStyleSheet(btn_style)

        for b in [self._btn_skip_prev, self._btn_back, self._btn_play,
                   self._btn_fwd, self._btn_skip_next]:
            l.addWidget(b)

        l.addSpacing(12)

        # 时间显示
        self._time_display = QLabel("00:00.00 / 00:00.00")
        self._time_display.setStyleSheet(
            f"color:{THEME['text_primary']}; font-size:13px; font-family:Consolas;"
        )
        l.addWidget(self._time_display)

        l.addSpacing(12)

        # 进度条
        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 10000)
        self._seek_slider.setStyleSheet(f"""
            QSlider::groove:horizontal{{background:{THEME['border']};height:6px;border-radius:3px;}}
            QSlider::handle:horizontal{{background:{THEME['accent']};width:14px;margin:-4px 0;border-radius:7px;}}
            QSlider::sub-page:horizontal{{background:{THEME['accent']}88;border-radius:3px;}}
        """)
        self._seek_slider.sliderMoved.connect(self._on_seek_slider)
        l.addWidget(self._seek_slider, 1)

        # 音量
        vol_label = QLabel("🔊")
        vol_label.setStyleSheet("font-size:14px;")
        l.addWidget(vol_label)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedWidth(80)
        self._vol_slider.valueChanged.connect(self.player.set_volume)
        l.addWidget(self._vol_slider)

        # 倍速
        l.addSpacing(8)
        self._speed_label = QLabel("1.0x")
        self._speed_label.setStyleSheet(
            f"color:{THEME['text_secondary']}; font-size:12px; min-width:36px;"
        )
        l.addWidget(self._speed_label)

        return w

    # ---- 底部工具栏 ----
    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background-color:{THEME['bg_card']}; border-top:1px solid {THEME['border']};"
        )
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
    #  信号连接
    # ==================================================================

    def _on_media_to_timeline(self, info: dict):
        """素材库双击 → 添加到时间轴"""
        cid = self.timeline.add_clip(info)
        if cid:
            self._status.setText(f"✅ 已添加: {info['name']}")
            self._update_project_tracks()

    def _on_media_selected(self, info: dict):
        """素材库选中 → 预览"""
        mt = info.get("type", "")
        if mt == "video" or mt == "audio":
            self.player.load_media(info["path"])
            self.player.play()
        elif mt == "image":
            self._status.setText(f"🖼️ 选中图片: {info['name']}")

    def _on_player_time_changed(self, time_sec: float):
        """播放器时间更新 → 同步进度条 + 播放头"""
        dur = self.player.get_duration()
        self._time_display.setText(
            f"{format_time(time_sec)} / {format_time(dur)}"
        )
        if dur > 0:
            self._seek_slider.setValue(int(time_sec / dur * 10000))
        self.timeline.set_playhead(time_sec)

    def _on_player_state_changed(self, state: str):
        """播放器状态变化"""
        if state == "playing":
            self._playing = True
            self._btn_play.setText("⏸")
        elif state in ("paused", "stopped", "ended"):
            self._playing = False
            self._btn_play.setText("▶")

    def _on_player_media_loaded(self, info: dict):
        """媒体加载完成"""
        self._seek_slider.setValue(0)
        self._time_display.setText(
            f"00:00.00 / {format_time(info['duration'])}"
        )

    def _on_timeline_playhead_moved(self, time_sec: float):
        """时间轴播放头拖动 → 播放器跳转"""
        self.player.seek(time_sec)

    def _on_timeline_clip_selected(self, clip_id: str, track_idx: int, clip_idx: int):
        """时间轴片段选中"""
        self._status.setText(f"选中片段: {clip_id[:8]} (轨道{track_idx})")

    def _on_timeline_clip_added(self, info: dict):
        """素材拖入时间轴 → 同步项目数据"""
        self._update_project_tracks()
        self._status.setText(f"✅ 已添加: {info.get('name', '?')}")

    # ==================================================================
    #  播放控制
    # ==================================================================

    def _on_play_pause(self):
        self.player.toggle_play_pause()

    def _seek_relative(self, delta: float):
        self.player.seek_relative(delta)

    def _on_seek_slider(self, value: int):
        dur = self.player.get_duration()
        if dur > 0:
            t = value / 10000.0 * dur
            self.player.seek(t)
            self.timeline.set_playhead(t)

    # ==================================================================
    #  项目数据同步
    # ==================================================================

    def _update_project_tracks(self):
        """从 timeline 同步轨道数据到 project（Phase 2 简化版）"""
        # 确保 project 有足够的轨道
        track_types = ["video", "audio", "audio", "subtitle"]
        while len(self.project.tracks) < len(track_types):
            idx = len(self.project.tracks)
            self.project.tracks.append(Track(
                type=track_types[idx] if idx < len(track_types) else "video",
                clips=[],
            ))

    # ==================================================================
    #  素材导入
    # ==================================================================

    def _on_import_media(self):
        """导入素材（文件对话框）"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "导入素材", "",
            "媒体文件 (*.mp4 *.mov *.mkv *.avi *.mp3 *.wav *.png *.jpg *.jpeg *.gif);;"
            "所有文件 (*.*)"
        )
        if files:
            self.media_bin.add_media_batch(files)

    # ==================================================================
    #  Phase 3: 切割 + 导出
    # ==================================================================

    def _on_cut(self):
        """在播放头位置切割"""
        t = self.timeline.get_playhead_time()
        count = self._cut_tool.cut_at_playhead(self.project, t)
        if count > 0:
            self.timeline.set_project(self.project)
            self._status.setText(f"✂️ 切割 {count} 个片段 @{format_time(t)}")
        else:
            self._status.setText(f"⚠️ 当前位置无可切割片段")

    def _on_delete_clip(self, clip_id: str):
        """删除选中片段"""
        if self.timeline.remove_clip(clip_id):
            self._update_project_tracks()
            self._status.setText(f"🗑️ 已删除片段")

    def _on_export(self):
        """导出视频"""
        from PyQt6.QtWidgets import QMessageBox

        if not self.project or not any(
            t.clips for t in self.project.tracks
        ):
            QMessageBox.information(self, "导出", "时间轴上没有素材，请先添加片段。")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出视频", self.project.name + ".mp4",
            "MP4 视频 (*.mp4);;所有文件 (*.*)"
        )
        if not path:
            return

        self._status.setText("📤 正在导出…")
        QApplication.processEvents()

        def on_progress(pct: float, msg: str):
            self._status.setText(f"📤 {msg}")
            QApplication.processEvents()

        ok = self._exporter.export(
            self.project, path,
            progress_callback=on_progress,
        )
        if ok:
            self._status.setText(f"✅ 导出完成: {path}")
        else:
            self._status.setText("❌ 导出失败")

    def _export_video(self, output_path: str, resolution: str,
                       fps: int, codec: str) -> bool:
        """AI 调用导出"""
        from src.ui.video_editor.data_models import ExporterConfig
        w, h = 1920, 1080
        if "x" in resolution:
            parts = resolution.split("x")
            w, h = int(parts[0]), int(parts[1])
        config = ExporterConfig(
            export_type="video", resolution=(w, h), fps=fps,
            codec=codec, output_format="mp4",
        )
        return self._exporter.export(self.project, output_path, config=config)

    # ---- 占位功能（Phase 4-6） ----

    def _on_start_recording(self):
        self._status.setText("🎥 录屏功能将在 Phase 4 实现")

    def _start_recording(self, config=None) -> bool:
        return False

    def _stop_recording(self):
        return None

    def _on_ai_dub(self):
        self._status.setText("🎙️ AI配音功能将在 Phase 5 实现")

    def _on_ai_subtitle(self):
        self._status.setText("📝 AI字幕功能将在 Phase 5 实现")

    def _on_open_cover(self):
        self._status.setText("🖼️ 封面制作功能将在 Phase 5 实现")

    def _open_cover_editor(self):
        pass

    def _ai_generate_cover(self, prompt: str):
        return None
