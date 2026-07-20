"""
视频剪辑器 — VLC 视频播放器

基于 python-vlc，提供播放/暂停/逐帧/倍速/截图等核心播放能力。

Phase 2: 基础播放 + 帧步进 + 音量控制
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QDialog
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from loguru import logger

from src.ui.video_editor.config import (
    PLAYER_VOLUME, PLAYER_LOOP, SEEK_STEP_SMALL, SEEK_STEP_LARGE,
    JKL_SPEED_MULTIPLIER, VLC_PATH, FFMPEG_PATH,
)
from src.ui.video_editor.styles import THEME
from src.ui.video_editor.utils import format_time, get_media_duration_ffprobe


# ---- VLC 导入 ----
try:
    import vlc
    VLC_AVAILABLE = True
except (ImportError, OSError):
    vlc = None
    VLC_AVAILABLE = False
    logger.warning("python-vlc 未安装或 VLC 未找到，播放器将使用降级模式")


class VideoPlayer(QWidget):
    """VLC 视频播放器控件

    信号：
        time_changed(float)     — 当前播放时间（秒）
        state_changed(str)      — 状态: playing / paused / stopped / ended
        media_loaded(dict)      — 媒体加载完成: {path, duration, resolution}
        error(str)              — 播放错误
    """

    time_changed = pyqtSignal(float)
    state_changed = pyqtSignal(str)
    media_loaded = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._vlc_instance: Optional["vlc.Instance"] = None
        self._media_player: Optional["vlc.MediaPlayer"] = None
        self._media_path: str = ""
        self._duration: float = 0.0
        self._current_state: str = "stopped"
        self._volume: int = PLAYER_VOLUME

        # 播放时间刷新定时器
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(33)  # ~30fps
        self._tick_timer.timeout.connect(self._on_tick)

        # 媒体结束检测定时器（VLC 某些平台 end_reached 不可靠）
        self._end_check_timer = QTimer(self)
        self._end_check_timer.setInterval(200)
        self._end_check_timer.timeout.connect(self._check_end)

        self._setup_ui()
        self._init_vlc()

    # ==================================================================
    #  UI
    # ==================================================================

    def _setup_ui(self):
        """构建播放器 UI 容器 + 全屏按钮叠加"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器（用于叠加全屏按钮）
        self._player_container = QWidget()
        self._player_container.setStyleSheet("background-color: #000;")
        cl = QVBoxLayout(self._player_container)
        cl.setContentsMargins(0, 0, 0, 0)

        # VLC 视频输出窗口（通过 winId 嵌入）
        self._video_widget = QWidget(self._player_container)
        self._video_widget.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self._video_widget.setStyleSheet("background-color: #000;")
        self._video_widget.setMinimumSize(440, 390)
        cl.addWidget(self._video_widget)

        layout.addWidget(self._player_container)

        # ---- 全屏按钮（叠加在右上角）----
        self._btn_fullscreen = QPushButton("⛶", self._player_container)
        self._btn_fullscreen.setToolTip("全屏播放")
        self._btn_fullscreen.setFixedSize(34, 28)
        self._btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_fullscreen.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,100);
                color: #ccc;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 15px;
            }
            QPushButton:hover {
                background: rgba(60,60,60,180);
                color: #fff;
                border-color: #999;
            }
        """)
        self._btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        self._btn_fullscreen.raise_()

        # 全屏窗口（延迟创建）
        self._fullscreen_win: Optional[QDialog] = None
        self._is_fullscreen: bool = False

    # ==================================================================
    #  VLC 初始化
    # ==================================================================

    def _init_vlc(self):
        """初始化 VLC 实例和播放器"""
        if not VLC_AVAILABLE:
            logger.warning("VLC 不可用，播放器处于纯黑模式")
            return

        try:
            # -- 指定 VLC 路径（便携版或安装版）
            args = []
            vlc_path = VLC_PATH
            if vlc_path.exists():
                args.append(f"--plugin-path={vlc_path / 'plugins'}")
                logger.info(f"VLC 路径: {vlc_path}")

            # 静默日志 + 硬件加速
            args += [
                "--quiet",
                "--no-video-title-show",
                "--avcodec-hw=any",
                "--no-snapshot-preview",
            ]

            self._vlc_instance = vlc.Instance(args)
            self._media_player = self._vlc_instance.media_player_new()

            # 嵌入到 PyQt 窗口
            if self._media_player and self._video_widget:
                win_id = int(self._video_widget.winId())
                self._media_player.set_hwnd(win_id)

            # 事件管理器
            if self._media_player:
                events = self._media_player.event_manager()
                events.event_attach(
                    vlc.EventType.MediaPlayerEndReached,
                    self._on_media_end,
                )
                events.event_attach(
                    vlc.EventType.MediaPlayerPlaying,
                    lambda _: self._on_state_change("playing"),
                )
                events.event_attach(
                    vlc.EventType.MediaPlayerPaused,
                    lambda _: self._on_state_change("paused"),
                )
                events.event_attach(
                    vlc.EventType.MediaPlayerStopped,
                    lambda _: self._on_state_change("stopped"),
                )

            logger.info("VLC 播放器初始化成功")

        except Exception as e:
            logger.error(f"VLC 初始化失败: {e}")
            self.error.emit(f"VLC 初始化失败: {e}")

    # ==================================================================
    #  公开 API
    # ==================================================================

    def load_media(self, file_path: str) -> bool:
        """Load media file.

        Duration detection (4-level fallback):
          1. ffprobe/ffmpeg (utils.get_media_duration_ffprobe)
          2. VLC media.parse_with_options + get_duration
          3. VLC get_duration retry (up to 5 times, 200ms each)
          4. VLC MediaPlayer.get_length
        """
        import time as _time

        if not Path(file_path).exists():
            msg = f"File not found: {file_path}"
            logger.warning(msg)
            self.error.emit(msg)
            return False

        self._media_path = file_path
        self.stop()

        # ---- Level 1: ffprobe/ffmpeg ----
        self._duration = get_media_duration_ffprobe(file_path) or 0.0
        logger.info(f"[Duration] L1(ffprobe): {self._duration:.1f}s")

        if self._media_player and self._vlc_instance:
            media = self._vlc_instance.media_new(file_path)
            self._media_player.set_media(media)

            # ---- Level 2: VLC parse + get_duration ----
            try:
                media.parse_with_options(vlc.MediaParseFlag.local, 5000)
                vlc_dur = media.get_duration() / 1000.0
                logger.info(f"[Duration] L2(VLC parse): {vlc_dur:.1f}s")
                if self._duration <= 0 and vlc_dur > 0:
                    self._duration = vlc_dur
            except Exception as e:
                logger.warning(f"VLC parse error: {e}")

            # ---- Level 3: retry get_duration ----
            if self._duration <= 0:
                for retry in range(5):
                    _time.sleep(0.2)
                    try:
                        vlc_dur = media.get_duration() / 1000.0
                        if vlc_dur > 0:
                            self._duration = vlc_dur
                            logger.info(f"[Duration] L3(retry#{retry+1}): {vlc_dur:.1f}s")
                            break
                    except Exception:
                        pass

            # ---- Level 4: MediaPlayer.get_length ----
            if self._duration <= 0:
                try:
                    mp_dur = self._media_player.get_length() / 1000.0
                    if mp_dur > 0:
                        self._duration = mp_dur
                        logger.info(f"[Duration] L4(MediaPlayer): {mp_dur:.1f}s")
                except Exception:
                    pass

        self.media_loaded.emit({
            "path": file_path,
            "duration": self._duration,
            "duration_str": format_time(self._duration),
        })

        logger.info(f"Loaded: {Path(file_path).name} ({format_time(self._duration)})")
        return True
    def play(self):
        """播放（VLC crash 保护）"""
        if not self._media_player or self._current_state == "playing":
            return
        try:
            result = self._media_player.play()
            if result == 0:
                self._tick_timer.start()
                self._end_check_timer.start()
            else:
                self.error.emit("播放失败")
        except Exception:
            logger.warning("VLC play() 异常，跳过")

    def pause(self):
        """暂停"""
        if not self._media_player or self._current_state != "playing":
            return
        self._media_player.pause()
        self._tick_timer.stop()
        self._end_check_timer.stop()

    def stop(self):
        """停止"""
        if self._media_player:
            self._media_player.stop()
        self._tick_timer.stop()
        self._end_check_timer.stop()
        self._current_state = "stopped"
        self.time_changed.emit(0)

    def toggle_play_pause(self):
        """切换播放/暂停"""
        if self._current_state == "playing":
            self.pause()
        else:
            self.play()

    def seek(self, time_sec: float) -> bool:
        """跳转到指定时间（秒）"""
        time_sec = max(0, min(time_sec, self._duration))
        if self._media_player and self._media_player.is_seekable():
            self._media_player.set_time(int(time_sec * 1000))
            self.time_changed.emit(time_sec)
            return True
        return False

    def seek_relative(self, delta_sec: float):
        """相对跳转"""
        current = self.get_time()
        self.seek(current + delta_sec)

    def step_frame(self, forward: bool = True):
        """逐帧步进（仅暂停时可用）"""
        if not self._media_player or self._current_state == "playing":
            return
        # VLC 没有原生逐帧 API，用时间近似
        fps = 30.0  # 默认
        delta = (1.0 / fps) if forward else (-1.0 / fps)
        self.seek_relative(delta)

    def set_playback_speed(self, speed: float):
        """设置播放速度（1.0=正常, 2.0=2倍速）"""
        if self._media_player:
            self._media_player.set_rate(speed)

    def set_volume(self, volume: int):
        """设置音量 0-100"""
        self._volume = max(0, min(100, volume))
        if self._media_player:
            self._media_player.audio_set_volume(self._volume)

    def get_time(self) -> float:
        """获取当前播放时间（秒）"""
        if self._media_player:
            return self._media_player.get_time() / 1000.0
        return 0.0

    def get_duration(self) -> float:
        """获取媒体时长（秒）"""
        return self._duration

    def is_playing(self) -> bool:
        return self._current_state == "playing"

    def snapshot(self, save_path: str) -> bool:
        """截取当前帧保存为图片"""
        if self._media_player:
            return self._media_player.video_take_snapshot(0, save_path, 0, 0) == 0
        return False

    # ==================================================================
    #  内部
    # ==================================================================

    def _on_tick(self):
        """定时刷新当前播放时间"""
        if self._media_player:
            t = self.get_time()
            self.time_changed.emit(t)

    def _on_media_end(self, event=None):
        """媒体播放结束"""
        if PLAYER_LOOP and self._media_player:
            self._media_player.stop()
            self._media_player.play()
        else:
            self._current_state = "ended"
            self._tick_timer.stop()
            self._end_check_timer.stop()
            self.state_changed.emit("ended")

    def _on_state_change(self, state: str):
        """播放状态变化"""
        self._current_state = state
        self.state_changed.emit(state)

    def _check_end(self):
        """定时检查是否已播放到结尾"""
        if self._media_player and self._duration > 0:
            t = self.get_time()
            if t >= self._duration - 0.1:
                self._on_media_end()

    # ==================================================================
    #  全屏
    # ==================================================================

    def resizeEvent(self, event):
        """窗口大小变化时重新定位全屏按钮"""
        super().resizeEvent(event)
        if hasattr(self, '_btn_fullscreen') and hasattr(self, '_player_container'):
            pw = self._player_container.width()
            self._btn_fullscreen.move(pw - 42, 8)
            self._btn_fullscreen.raise_()

    def _toggle_fullscreen(self):
        """切换全屏"""
        if self._is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        """进入全屏：创建独立全屏窗口，把 VLC 渲染目标切过去"""
        if not self._media_player:
            return

        self._is_fullscreen = True
        self._btn_fullscreen.setText("⛷")
        self._btn_fullscreen.setToolTip("退出全屏")

        # 创建无边框全屏窗口
        self._fullscreen_win = QDialog(
            None,
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint,
        )
        self._fullscreen_win.setStyleSheet("background-color: #000;")

        # VLC 渲染目标 widget
        self._fs_video = QWidget(self._fullscreen_win)
        self._fs_video.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        fsl = QVBoxLayout(self._fullscreen_win)
        fsl.setContentsMargins(0, 0, 0, 0)
        fsl.addWidget(self._fs_video)

        # 退出按钮
        self._fs_close_btn = QPushButton("✕ 退出全屏", self._fullscreen_win)
        self._fs_close_btn.setFixedSize(100, 30)
        self._fs_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fs_close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,140);
                color: #ccc;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(200,50,50,180);
                color: #fff;
            }
        """)
        self._fs_close_btn.clicked.connect(self._exit_fullscreen)

        # 定时隐藏退出按钮
        self._fs_hide_timer = QTimer(self._fullscreen_win)
        self._fs_hide_timer.setInterval(1500)
        self._fs_hide_timer.timeout.connect(self._fs_close_btn.hide)

        # 鼠标移动显示按钮 + ESC 退出
        self._fs_video.setMouseTracking(True)
        self._fs_video.installEventFilter(self)
        self._fullscreen_win.installEventFilter(self)

        # 把 VLC 渲染切到全屏窗口
        fs_win_id = int(self._fs_video.winId())
        self._media_player.set_hwnd(fs_win_id)

        # 显示
        self._video_widget.hide()
        screen_geo = self.screen().geometry()
        self._fullscreen_win.setGeometry(screen_geo)
        self._fullscreen_win.showFullScreen()
        self._fullscreen_win.setFocus()

        logger.info("进入全屏播放")

    def _exit_fullscreen(self):
        """退出全屏：VLC 渲染切回原窗口"""
        self._is_fullscreen = False
        self._btn_fullscreen.setText("⛶")
        self._btn_fullscreen.setToolTip("全屏播放")

        # VLC 渲染切回原 widget
        if self._media_player:
            win_id = int(self._video_widget.winId())
            self._media_player.set_hwnd(win_id)

        self._video_widget.show()

        if self._fullscreen_win:
            self._fullscreen_win.close()
            self._fullscreen_win.deleteLater()
            self._fullscreen_win = None
            self._fs_video = None
            self._fs_close_btn = None

        logger.info("退出全屏播放")

    def eventFilter(self, obj, event):
        """全屏窗口：鼠标移动显示退出按钮 / ESC 退出全屏"""
        from PyQt6.QtCore import QEvent
        if self._is_fullscreen:
            # 鼠标移动 → 显示退出按钮
            if (obj is getattr(self, '_fs_video', None)
                    and event.type() == QEvent.Type.MouseMove):
                if hasattr(self, '_fs_close_btn') and self._fs_close_btn:
                    self._fs_close_btn.show()
                    fw = self._fullscreen_win.width() if self._fullscreen_win else 1920
                    self._fs_close_btn.move(fw - 110, 12)
                    self._fs_close_btn.raise_()
                    if hasattr(self, '_fs_hide_timer'):
                        self._fs_hide_timer.start()
            # ESC → 退出全屏
            elif (obj is self._fullscreen_win
                    and event.type() == QEvent.Type.KeyPress
                    and event.key() == Qt.Key.Key_Escape):
                self._exit_fullscreen()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """清理 VLC 资源"""
        self.stop()
        if self._media_player:
            self._media_player.release()
            self._media_player = None
        if self._vlc_instance:
            self._vlc_instance.release()
            self._vlc_instance = None
        super().closeEvent(event)

    # ==================================================================
    #  降级模式（VLC 不可用时）
    # ==================================================================

    @property
    def vlc_available(self) -> bool:
        return VLC_AVAILABLE and self._media_player is not None
