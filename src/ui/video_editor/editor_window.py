"""
视频剪辑器 — 主窗口 (VideoEditorPage)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QPushButton, QSlider, QFrame, QFileDialog, QApplication, QDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from loguru import logger

from ..theme import THEME
from src.ui.video_editor.data_models import (
    Project, RecordingConfig, Track, Clip, ExporterConfig, SubtitleClip,
)
from src.ui.video_editor.project_manager import ProjectManager
from src.ui.video_editor.commands import UndoManager
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # 仅供类型注解，避免与 editor_api 形成模块级循环导入
    from src.ui.video_editor.editor_api import EditorAPI
from src.ui.video_editor.player import VideoPlayer
from src.ui.video_editor.media_bin import MediaBin
from src.ui.video_editor.timeline import TimelineView
from src.ui.video_editor.cut_tool import CutTool
from src.ui.video_editor.exporter import Exporter
from src.ui.video_editor.screen_recorder import ScreenRecorder
from src.ui.video_editor.recorder_overlay import RecorderOverlay
from src.ui.video_editor.recorder_settings import RecorderSettingsDialog
from src.ui.video_editor.ai_clip_engine import AIClipEngine
from src.ui.video_editor.ai_dub_engine import AIDubEngine
from src.ui.video_editor.ai_subtitle_engine import AISubtitleEngine
from src.ui.video_editor.cover_editor import CoverEditor
from src.ui.video_editor.cover_ai_engine import CoverAIEngine
from src.ui.video_editor.ai_video_maker import AIVideoMaker
from src.ui.video_editor.ai_video_panel import AIVideoPanel
from src.ui.video_editor.color_filter import ColorFilterEngine
from src.ui.video_editor.transition_engine import TransitionEngine, ALL_TRANSITIONS
from src.ui.video_editor.keyframe import KeyframeManager
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
        from src.ui.video_editor.editor_api import EditorAPI  # 延迟导入，打破循环
        self._api = EditorAPI(self)
        self.project = self._pm.new_project()
        self._playing = False
        self._cut_tool = CutTool()
        self._exporter = Exporter()
        self._recorder = ScreenRecorder()
        self._last_preview_path = ""  # 防重复预览
        self._recorder.on_time_updated = self._on_recording_time
        self._recorder.on_state_changed = self._on_recording_state
        self._recorder.on_error = self._on_recording_error
        self._overlay = RecorderOverlay()
        self._overlay.pause_clicked.connect(self._on_overlay_pause)
        self._overlay.resume_clicked.connect(self._on_overlay_resume)
        self._overlay.stop_clicked.connect(self._on_overlay_stop)
        self._overlay.overlay_closed.connect(self._on_overlay_closed)
        self._recording_timer = QTimer(self)
        self._recording_timer.setInterval(200)
        self._recording_timer.timeout.connect(self._update_recording_time)
        # Phase 5: AI 引擎
        self._ai_clip = AIClipEngine(self)
        self._dub_engine = AIDubEngine()
        self._dub_engine.finished.connect(self._on_dub_finished)
        self._subtitle_engine = AISubtitleEngine()
        self._subtitle_engine.finished.connect(self._on_subtitle_finished)
        self._cover_editor: CoverEditor | None = None
        self._cover_ai = CoverAIEngine()
        self._cover_ai.finished.connect(self._on_cover_ai_finished)
        self._ai_video_maker = None
        self._ai_video_panel = None
        self._setup_ui()

        # 启动时清理孤儿 ffmpeg 录屏进程（防止上次异常退出残留）
        orphan_count = ScreenRecorder.kill_orphan_ffmpeg()
        if orphan_count > 0:
            logger.info(f"启动时清理了 {orphan_count} 个孤儿录屏进程")

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
        rl.addWidget(self.player, 8)

        # 播放控制栏
        self._player_controls = self._build_player_controls()
        rl.addWidget(self._player_controls)

        splitter.addWidget(right)
        splitter.setSizes([160, 860])

        layout.addWidget(splitter)

        # ---- 时间轴 ----
        self.timeline = TimelineView()
        self.timeline.set_project(self.project)
        self.timeline.playhead_moved.connect(self._on_timeline_playhead_moved)
        self.timeline.clip_selected.connect(self._on_timeline_clip_selected)
        self.timeline.clip_added_to_timeline.connect(self._on_timeline_clip_added)
        self.timeline.cut_requested.connect(self._on_cut)
        self.timeline.delete_requested.connect(self._on_delete_clip)
        self.timeline.clip_trimmed.connect(self._on_clip_trim)

        # ---- 剪辑工具栏（素材库/播放器下方、时间轴上方） ----
        self._clip_toolbar = self._build_clip_toolbar()
        layout.addWidget(self._clip_toolbar)

        layout.addWidget(self.timeline, 1)

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
        self._btn_skip_prev.clicked.connect(self._on_skip_prev)

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
        self._btn_skip_next.clicked.connect(self._on_skip_next)

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

        # 全屏按钮
        l.addSpacing(8)
        self._btn_fullscreen = QPushButton("⛶ 全屏")
        self._btn_fullscreen.setToolTip("全屏播放 (F)")
        self._btn_fullscreen.setStyleSheet(btn_style)
        self._btn_fullscreen.clicked.connect(self._on_fullscreen)
        l.addWidget(self._btn_fullscreen)

        return w

    # ---- 底部工具栏 ----
    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background-color:{THEME['bg_card']}; border-top:1px solid {THEME['border']};"
        )
        l = QHBoxLayout(w)
        l.setContentsMargins(8, 4, 8, 4)
        l.setSpacing(6)

        # ==== 文件 & 录制 ====
        file_btns = [
            ("💾 保存", self._on_save_project, "保存项目 (Ctrl+S)"),
            ("📂 打开", self._on_load_project, "打开项目 / 导入媒体"),
            ("🎥 录屏", self._on_start_recording, "录制屏幕"),
        ]
        for text, handler, tip in file_btns:
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setStyleSheet(TOOLBAR_STYLESHEET)
            btn.clicked.connect(handler)
            l.addWidget(btn)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"color:{THEME['border']};")
        l.addWidget(sep2)

        # ==== AI & 后期 ====
        ai_btns = [
            ("🎙️ AI配音", self._on_ai_dub, "AI 文字转语音"),
            ("📝 AI字幕", self._on_ai_subtitle, "AI 语音识别字幕"),
            ("🎨 滤镜", self._on_filter_panel, "颜色滤镜调节"),
            ("🎬 转场", self._on_add_transition, "片段间转场效果"),
            ("🎯 关键帧", self._on_keyframe_panel, "关键帧动画"),
            ("🖼️ 封面", self._on_open_cover, "制作视频封面"),
            ("🤖 AI视频", self._on_ai_video, "AI 图文成片"),
        ]
        for text, handler, tip in ai_btns:
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setStyleSheet(TOOLBAR_STYLESHEET)
            btn.clicked.connect(handler)
            l.addWidget(btn)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet(f"color:{THEME['border']};")
        l.addWidget(sep3)

        # ==== 导出 ====
        export_btn = QPushButton("📤 导出")
        export_btn.setToolTip("导出为 MP4 视频")
        export_btn.setStyleSheet(TOOLBAR_STYLESHEET)
        export_btn.clicked.connect(self._on_export)
        l.addWidget(export_btn)

        l.addStretch()
        return w

    # ---- 剪辑工具栏（素材库下方、时间轴上方） ----
    def _build_clip_toolbar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background-color:{THEME['bg_card']};"
            f"border-top:1px solid {THEME['border']};"
            f"border-bottom:1px solid {THEME['border']};"
        )
        l = QHBoxLayout(w)
        l.setContentsMargins(8, 3, 8, 3)
        l.setSpacing(6)

        clip_label = QLabel("🔧 剪辑工具")
        clip_label.setStyleSheet(
            f"color:{THEME['text_secondary']}; font-size:12px; font-weight:bold;"
        )
        l.addWidget(clip_label)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.Shape.VLine)
        sep0.setStyleSheet(f"color:{THEME['border']};")
        l.addWidget(sep0)

        edit_btns = [
            ("✂️ 切割", self._on_cut, "在播放头位置切割 (S / Ctrl+K)"),
            ("🗑️ 删除", self._on_delete_selected, "删除选中片段 (Delete)"),
            ("↩️ 撤销", self._on_undo, "撤销 (Ctrl+Z)"),
            ("↪️ 重做", self._on_redo, "重做 (Ctrl+Y)"),
        ]
        for text, handler, tip in edit_btns:
            btn = QPushButton(text)
            btn.setToolTip(tip)
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
        logger.info(f"[双击] 开始添加素材: {info.get('name','?')} type={info.get('type')}")
        try:
            logger.info("[双击] 调用 timeline.add_clip...")
            cid = self.timeline.add_clip(info)
            logger.info(f"[双击] add_clip 返回: {cid}")
            if cid:
                self._status.setText(f"✅ 已添加: {info['name']}")
                logger.info("[双击] 调用 _update_project_tracks...")
                self._update_project_tracks()
                logger.info("[双击] _update_project_tracks 完成")
        except Exception as e:
            logger.exception(f"添加素材到时间轴失败: {e}")
            self._status.setText(f"❌ 添加失败: {info.get('name', '未知')}")
        logger.info("[双击] _on_media_to_timeline 完成")

    def _on_media_selected(self, info: dict):
        """素材库选中 → 预览播放（不重复加载同一文件）"""
        try:
            mt = info.get("type", "")
            if mt in ("video", "audio"):
                if self.player.vlc_available:
                    path = info["path"]
                    # 同一文件不重复加载/播放
                    if getattr(self, '_last_preview_path', '') == path:
                        return
                    self._last_preview_path = path
                    self.player.load_media(path)
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(500, self.player.play)
            elif mt == "image":
                self._status.setText(f"🖼️ 选中图片: {info['name']}")
        except Exception as e:
            logger.warning(f"预览媒体失败: {e}")

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

    def keyPressEvent(self, event):
        """键盘快捷键"""
        from PyQt6.QtCore import Qt as Qtc
        if event.key() == Qtc.Key.Key_F and not event.isAutoRepeat():
            self.player.toggle_fullscreen()
            return
        super().keyPressEvent(event)

    def _on_play_pause(self):
        self.player.toggle_play_pause()

    def _seek_relative(self, delta: float):
        self.player.seek_relative(delta)

    # ---- EditorAPI / AI引擎 桥接方法 ----

    def _media_bin_add(self, info: dict):
        self.media_bin._add_to_list(info)

    def _timeline_refresh(self):
        self.timeline.set_project(self.project)

    def _player_play(self):
        self.player.play()

    def _player_pause(self):
        self.player.pause()

    def _player_seek(self, time_sec: float):
        self.player.seek(time_sec)

    def _player_get_time(self) -> float:
        return self.player.get_time()

    def _on_start_recording(self):
        self._start_recording()

    def _on_skip_prev(self):
        """跳到上一个剪辑点"""
        t = self.player.get_time()
        points = []
        for track in self.project.tracks:
            for clip in track.clips:
                points.append(clip.timeline_start)
                points.append(clip.timeline_start + clip.effective_duration)
        points = sorted(set(p for p in points if p < t - 0.05))
        if points:
            self.player.seek(points[-1])
            self.timeline.set_playhead(points[-1])

    def _on_skip_next(self):
        """跳到下一个剪辑点"""
        t = self.player.get_time()
        points = []
        for track in self.project.tracks:
            for clip in track.clips:
                points.append(clip.timeline_start)
                points.append(clip.timeline_start + clip.effective_duration)
        points = sorted(set(p for p in points if p > t + 0.05))
        if points:
            self.player.seek(points[0])
            self.timeline.set_playhead(points[0])

    def _on_fullscreen(self):
        """全屏切换"""
        self.player.toggle_fullscreen()

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
        """在播放头位置切割（支持撤销）"""
        t = self.timeline.get_playhead_time()
        old_clips_data = []
        for ti, track in enumerate(self.project.tracks):
            if track.type in ("video", "audio"):
                for ci, clip in enumerate(track.clips):
                    if isinstance(clip, Clip):
                        clip_start = clip.timeline_start
                        clip_end = clip_start + clip.effective_duration
                        if clip_start + 0.05 < t < clip_end - 0.05:
                            old_clips_data.append((ti, ci, clip.timeline_start, {
                                "id": clip.id, "source_path": clip.source_path,
                                "type": clip.type, "track_index": clip.track_index,
                                "timeline_start": clip.timeline_start,
                                "source_start": clip.source_start,
                                "source_end": clip.source_end,
                                "duration": clip.duration, "speed": clip.speed,
                            }, clip.source_end))

        count = self._cut_tool.cut_at_playhead(self.project, t)
        if count > 0:
            for ti, ci, st, cd, old_se in old_clips_data:
                new_se = cd["source_start"] + (t - st) * cd["speed"]
                new_clip_data = {
                    "id": cd["id"] + "_r", "source_path": cd["source_path"],
                    "type": cd["type"], "track_index": cd["track_index"],
                    "timeline_start": t,
                    "source_start": new_se, "source_end": cd["source_end"],
                    "duration": cd["source_end"] - new_se, "speed": cd["speed"],
                }
                from src.ui.video_editor.commands import SplitClipCommand
                cmd = SplitClipCommand(ti, ci, st, new_clip_data, old_se, new_se)
                self._undo_manager.execute(cmd, self.project)
            self.timeline.set_project(self.project)
            self._status.setText(f"✂️ 切割 {count} 个片段 @{format_time(t)} (Ctrl+Z 撤销)")
        else:
            self._status.setText(f"⚠️ 当前位置无可切割片段")

    def _on_delete_selected(self):
        """删除当前选中的片段 (工具栏按钮)"""
        cid = self.timeline.get_selected_clip_id()
        if cid:
            self._on_delete_clip(cid)
        else:
            self._status.setText("⚠️ 请先在时间轴上选中一个片段")

    def _on_clip_trim(self, clip_id, old_ts, new_ts, old_ss, new_ss, old_se, new_se, old_dur, new_dur):
        """裁剪手柄释放 → 注册撤销命令"""
        for ti, track in enumerate(self.project.tracks):
            for ci, clip in enumerate(track.clips):
                if isinstance(clip, Clip) and clip.id == clip_id:
                    from src.ui.video_editor.commands import TrimClipCommand
                    cmd = TrimClipCommand(ti, ci, old_ts, new_ts, old_ss, new_ss, old_se, new_se, old_dur, new_dur)
                    self._undo_manager.execute(cmd, self.project)
                    self._status.setText(f"✂️ 裁剪: {old_dur:.1f}s→{new_dur:.1f}s (Ctrl+Z 撤销)")
                    return

    def _on_undo(self):
        """撤销上一步操作"""
        if self._undo_manager.can_undo:
            desc = self._undo_manager.undo_description
            if self._undo_manager.undo(self.project):
                self.timeline.set_project(self.project)
                self._status.setText(f"↩️ 已撤销: {desc}")
            else:
                self._status.setText("↩️ 撤销失败")
        else:
            self._status.setText("↩️ 没有可撤销的操作")

    def _on_redo(self):
        """重做被撤销的操作"""
        if self._undo_manager.can_redo:
            if self._undo_manager.redo(self.project):
                self.timeline.set_project(self.project)
                self._status.setText("↪️ 已重做")
            else:
                self._status.setText("↪️ 重做失败")
        else:
            self._status.setText("↪️ 没有可重做的操作")

    def _on_delete_clip(self, clip_id: str):
        """删除选中片段"""
        ti, ci = self.timeline.get_clip_track_and_index(clip_id)
        if ti >= 0 and ci >= 0 and ti < len(self.project.tracks):
            track = self.project.tracks[ti]
            if ci < len(track.clips):
                clip = track.clips[ci]
                from src.ui.video_editor.data_models import Clip as ClipModel
                if isinstance(clip, ClipModel):
                    cd = {
                        "id": clip.id, "source_path": clip.source_path,
                        "type": clip.type, "track_index": clip.track_index,
                        "timeline_start": clip.timeline_start,
                        "source_start": clip.source_start,
                        "source_end": clip.source_end,
                        "duration": clip.duration, "speed": clip.speed,
                    }
                else:
                    cd = {"id": getattr(clip, "id", ""), "type": getattr(clip, "type", "video"),
                           "track_index": ti, "timeline_start": 0.0, "source_start": 0.0,
                           "source_end": 0.0, "duration": 0.0, "speed": 1.0}
                from src.ui.video_editor.commands import DeleteClipCommand
                cmd = DeleteClipCommand(ti, ci, cd)
                self._undo_manager.execute(cmd, self.project)
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

    # ---- Phase 4: 录屏 ----

    def _on_start_recording(self):
        dlg = RecorderSettingsDialog(
            RecordingConfig(output_dir=self.media_bin._root_dir if hasattr(self.media_bin, '_root_dir') else ''),
            self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # 对话框关闭后延迟启动录制，避免在 modal 内操作 GUI
            config = dlg.get_config()
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._start_recording_with_config(config))

    def _start_recording_with_config(self, config: RecordingConfig):
        # 先显示控制条（秒出），再异步启动录制引擎
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.activateWindow()
        self._status.setText("🔴 正在启动录制…")
        self._recording_starting = True

        def _do_start():
            ok = self._recorder.start(config)
            from PyQt6.QtCore import QTimer
            if ok and self._recording_starting:
                QTimer.singleShot(0, lambda: (
                    self._status.setText("🔴 正在录制…"),
                    self._recording_timer.start(),
                    setattr(self, '_recording_starting', False),
                ))
            else:
                QTimer.singleShot(0, lambda: (
                    self._overlay.hide(),
                    self._status.setText("❌ 录制启动失败"),
                    setattr(self, '_recording_starting', False),
                ))

        import threading
        threading.Thread(target=_do_start, daemon=True).start()

    def _start_recording(self, config=None) -> bool:
        cfg = config or RecordingConfig()
        return self._recorder.start(cfg)

    def _stop_recording(self):
        self._recording_starting = False
        self._recording_timer.stop()
        self._overlay.hide()
        result = self._recorder.stop()
        if result:
            self.media_bin.add_media_batch([result])
            self._status.setText(f"✅ 录制完成: {result}")
        return result

    def _on_recording_time(self, seconds: float):
        self._overlay.set_time(seconds)

    def _update_recording_time(self):
        """主线程安全：轮询录制时间并更新 overlay"""
        if self._recorder.is_recording:
            self._overlay.set_time(self._recorder.elapsed)

    def _on_recording_state(self, state: str):
        if state == "paused":
            self._status.setText("⏸ 录制已暂停")
        elif state == "recording":
            self._status.setText("🔴 正在录制…")
        elif state == "stopped":
            self._status.setText("✅ 录制已停止")

    def _on_recording_error(self, msg: str):
        self._status.setText(f"❌ 录制错误: {msg}")
        # 保持 overlay 显示 3 秒让用户看到错误，然后自动隐藏
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self._overlay.hide)

    def _on_overlay_pause(self):
        self._recorder.pause()

    def _on_overlay_resume(self):
        self._recorder.resume()

    def _on_overlay_stop(self):
        self._stop_recording()

    def _on_overlay_closed(self):
        if self._recorder.is_recording:
            self._recorder.stop()

    # ==================================================================
    #  Phase 5: AI 引擎集成
    # ==================================================================

    # ---- AI 剪辑 ----

    def process_ai_command(self, text: str) -> str:
        """ChatPage 调用入口：处理 AI 剪辑指令"""
        return self._ai_clip.process(text)

    # ---- AI 配音 ----

    def _on_ai_dub(self):
        """打开 AI 配音对话框"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(
            self, "AI 配音", "输入要配音的文字:"
        )
        if ok and text.strip():
            self._on_ai_dub_real(text.strip())

    def _on_ai_dub_real(self, text: str):
        """真实 AI 配音执行"""
        self._status.setText(f"🎙️ AI配音中: {text[:30]}…")
        self._dub_engine.speak(text)

    def _on_dub_finished(self, result):
        """配音完成 → 导入素材库 + 时间轴"""
        from src.ui.video_editor.data_models import Clip
        self.media_bin.add_media_batch([result.audio_path])
        self._status.setText(f"✅ AI配音完成 ({result.duration:.1f}s, {result.engine})")

    # ---- AI 字幕 ----

    def _on_ai_subtitle(self):
        """打开 AI 字幕对话框"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频/音频文件", "",
            "媒体文件 (*.mp4 *.mov *.avi *.mkv *.mp3 *.wav);;所有文件 (*.*)"
        )
        if files:
            self._on_ai_subtitle_real(files[0])

    def _on_ai_subtitle_real(self, source: str = ""):
        """真实 AI 字幕生成"""
        if not source:
            # 使用当前项目中的第一个视频
            clips = self.project.all_clips
            video_clips = [c for c in clips if c.type == "video"]
            if video_clips:
                source = video_clips[0].source_path
            else:
                self._status.setText("⚠️ 请先导入视频文件")
                return
        ext = Path(source).suffix.lower()
        self._status.setText(f"📝 AI字幕识别中…")
        if ext in (".mp4", ".mov", ".avi", ".mkv"):
            self._subtitle_engine.generate_from_video(source)
        else:
            self._subtitle_engine.generate_from_audio(source)

    def _on_subtitle_finished(self, clips_data: list):
        """字幕识别完成 → 添加到字幕轨"""
        if not clips_data:
            self._status.setText("⚠️ 未识别到语音内容")
            return
        for cd in clips_data:
            sc = SubtitleClip(
                id=generate_clip_id(),
                text=cd["text"], start_time=cd["start_time"],
                end_time=cd["end_time"], track_index=3,
                font=cd.get("font", "Microsoft YaHei"),
                font_size=cd.get("font_size", 28),
                color=cd.get("color", "#FFFFFF"),
                position=cd.get("position", "bottom"),
                has_outline=cd.get("has_outline", True),
            )
            self.timeline.add_subtitle(sc)
        self._status.setText(f"✅ 已生成 {len(clips_data)} 条字幕")

    # ---- 封面制作 ----

    def _on_open_cover(self):
        """打开封面编辑器"""
        self._cover_editor = CoverEditor()
        self._cover_editor.finished.connect(self._on_cover_exported)
        # 如果有已保存的封面数据，恢复
        if self.project.cover_data:
            self._cover_editor.load_cover_data(self.project.cover_data)
        self._cover_editor.setWindowTitle("封面制作 — 青锋")
        self._cover_editor.resize(1100, 700)
        self._cover_editor.show()

    def _on_cover_exported(self, path: str):
        """封面导出完成"""
        self.project.cover_data = self._cover_editor.get_cover_data() if self._cover_editor else None
        self._status.setText(f"🖼️ 封面已导出: {path}")

    def _on_ai_generate_cover_real(self, title: str):
        """AI 生成封面 → 打开编辑器预览"""
        self._status.setText(f"🤖 AI封面生成中: {title}")
        result = self._cover_ai.generate(title)
        # 打开编辑器预览
        if not self._cover_editor:
            self._cover_editor = CoverEditor()
            self._cover_editor.finished.connect(self._on_cover_exported)
        self._cover_editor.load_result(result)
        self._cover_editor.setWindowTitle(f"封面制作 — {title}")
        self._cover_editor.resize(1100, 700)
        self._cover_editor.show()
        self._status.setText(f"🖼️ AI封面已生成，可在编辑器中微调")

    def _on_cover_ai_finished(self, result: dict):
        """AI 封面引擎异步完成"""
        if self._cover_editor:
            self._cover_editor.load_result(result)

    def _open_cover_editor(self):
        """API 兼容：打开封面编辑器"""
        self._on_open_cover()

    def _ai_generate_cover(self, prompt: str):
        """API 兼容：AI 生成封面"""
        self._on_ai_generate_cover_real(prompt)

    # ---- AI 剪辑辅助方法 ----

    def _delete_clip_by_index(self, idx: int):
        """按索引删除片段"""
        clips = self.project.all_clips
        if 0 <= idx < len(clips):
            self.timeline.remove_clip(clips[idx].id)
            self._update_project_tracks()

    def _sync_timeline(self):
        """同步 project 到 timeline 显示"""
        self.timeline.set_project(self.project)

    def _update_clip_display(self, clip: Clip):
        """更新单个片段的显示"""
        self.timeline.set_project(self.project)

    # ==================================================================
    #  Phase 6: 保存 / 加载
    # ==================================================================

    def _on_save_project(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        if not self.project.file_path:
            path, _ = QFileDialog.getSaveFileName(
                self, "保存项目", self.project.name + ".7tanproj",
                "7tan 项目 (*.7tanproj);;所有文件 (*.*)"
            )
            if not path:
                return
            self.project.file_path = path
        ok = self._pm.save(self.project)
        if ok:
            self._status.setText(f"💾 已保存: {self.project.file_path}")
        else:
            QMessageBox.warning(self, "保存失败", "项目保存失败，请检查磁盘空间。")

    def _on_load_project(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "",
            "7tan 项目 (*.7tanproj);;所有文件 (*.*)"
        )
        if not path:
            return
        p = self._pm.load(path)
        if p:
            self.project = p
            self.timeline.set_project(p)
            self._status.setText(f"📂 已打开: {path}")
        else:
            QMessageBox.warning(self, "打开失败", "无法加载项目文件。")

    # ==================================================================
    #  Phase 6: 滤镜
    # ==================================================================

    def _on_filter_panel(self):
        clips = self.project.all_clips
        if not clips:
            self._status.setText("⚠️ 请先添加视频片段")
            return
        from src.ui.video_editor.filter_panel import FilterPanel
        dlg = FilterPanel(clips[0], self)
        dlg.filter_applied.connect(lambda c: self._on_filter_applied(c))
        dlg.exec()

    def _on_filter_applied(self, clip: "Clip"):
        self._status.setText(f"🎨 滤镜已应用: {clip.id[:8]}")
        self._update_project_tracks()

    # ==================================================================
    #  Phase 6: 转场
    # ==================================================================

    def _on_add_transition(self):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        pairs = TransitionEngine.get_clip_pairs_for_transitions(self.project.tracks)
        if not pairs:
            QMessageBox.information(self, "转场", "需要至少两个相邻的视频片段才能添加转场。")
            return
        names = list(ALL_TRANSITIONS.keys())
        name, ok = QInputDialog.getItem(self, "添加转场", "选择转场类型:", names, 0, False)
        if not ok or not name:
            return
        dur_str, ok2 = QInputDialog.getDouble(self, "转场时长", "持续秒数:", 0.5, 0.1, 5.0, 1)
        if not ok2:
            return
        prev_clip, next_clip, _ = pairs[0]
        TransitionEngine.apply_transition(self.project, prev_clip.id, next_clip.id, name, dur_str)
        td = ALL_TRANSITIONS.get(name)
        self._status.setText(f"🎬 已添加转场: {td.display_name if td else name} ({dur_str}s)")

    # ==================================================================
    #  Phase 6: 关键帧
    # ==================================================================

    def _on_keyframe_panel(self):
        clips = self.project.all_clips
        if not clips:
            self._status.setText("⚠️ 请先添加视频片段")
            return
        from src.ui.video_editor.keyframe_panel import KeyframePanel
        dlg = KeyframePanel(clips[0], self)
        dlg.keyframes_changed.connect(lambda c: self._on_keyframes_changed(c))
        dlg.exec()

    def _on_keyframes_changed(self, clip: "Clip"):
        kf_count = len(getattr(clip, 'keyframes', []) or [])
        self._status.setText(f"🎯 关键帧已更新: {clip.id[:8]} ({kf_count} 个)")
        self._update_project_tracks()

    # ==================================================================
    #  Phase 7: AI 视频制作（图文成片）
    # ==================================================================

    def _on_ai_video(self):
        if not self._ai_video_maker:
            self._ai_video_maker = AIVideoMaker(
                editor_api=self._api, dub_engine=self._dub_engine,
                media_bin=self.media_bin)
        self._ai_video_panel = AIVideoPanel()
        self._ai_video_panel.script_generated.connect(self._on_ai_video_script_generated)
        self._ai_video_panel.pipeline_requested.connect(self._on_ai_video_pipeline)
        self._ai_video_panel.setWindowTitle("🤖 AI 视频制作 — 青锋")
        self._ai_video_panel.resize(520, 600)
        self._ai_video_panel.show()

    def _on_ai_video_script_generated(self, params: dict):
        topic = params.get("topic", "")
        style = params.get("style", "professional")
        target_duration = params.get("duration", 180)
        self._status.setText(f"🤖 AI 正在生成脚本: {topic[:40]}…")
        try:
            import threading
            def _gen():
                script = self._ai_video_maker.generate_script(topic, style, target_duration)
                from PyQt6.QtCore import QMetaObject, Qt as Qtc, Q_ARG
                if self._ai_video_panel:
                    QMetaObject.invokeMethod(self._ai_video_panel, "set_script",
                        Qtc.ConnectionType.QueuedConnection, Q_ARG(object, script))
                    QMetaObject.invokeMethod(self._ai_video_panel, "on_generation_done",
                        Qtc.ConnectionType.QueuedConnection)
                self._status.setText(f"✅ 脚本: {script.title} ({len(script.scenes)} 个场景)")
            threading.Thread(target=_gen, daemon=True).start()
        except Exception as e:
            self._status.setText(f"❌ 脚本生成失败: {e}")
            if self._ai_video_panel:
                self._ai_video_panel.on_generation_done()

    def _on_ai_video_pipeline(self, params: dict):
        topic = params.get("topic", "")
        mode = params.get("mode", "text_only")
        style = params.get("style", "professional")
        target_duration = params.get("duration", 180)
        voice = params.get("voice", "female_gentle")
        self._status.setText(f"🚀 AI 视频制作开始: {topic[:40]}…")
        import threading
        def _run():
            def on_progress(status, progress, message):
                from PyQt6.QtCore import QMetaObject, Qt as Qtc, Q_ARG
                from src.ui.video_editor.data_models import AIVideoTask
                t = AIVideoTask(status=status, progress=progress, message=message)
                if self._ai_video_panel:
                    QMetaObject.invokeMethod(self._ai_video_panel, "set_task",
                        Qtc.ConnectionType.QueuedConnection, Q_ARG(object, t))
                self._status.setText(f"🤖 [{status}] {message}")
            task = self._ai_video_maker.run_full_pipeline(
                topic=topic, project=self.project, mode=mode,
                style=style, target_duration=target_duration,
                voice=voice, on_progress=on_progress)
            from PyQt6.QtCore import QMetaObject, Qt as Qtc
            if self._ai_video_panel:
                QMetaObject.invokeMethod(self._ai_video_panel, "on_pipeline_done",
                    Qtc.ConnectionType.QueuedConnection)
            self._update_project_tracks()
            ok = "✅" if task.status == "done" else "❌"
            self._status.setText(f"{ok} {task.message}")
        threading.Thread(target=_run, daemon=True).start()
