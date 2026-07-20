"""
视频剪辑器 — 时间轴 QGraphicsScene 元素

包含片段块、轨道背景、时间标尺、播放头等可绘制元素。

Phase 3: 右键菜单支持 + 吸附增强
"""

from typing import Optional
import os
import subprocess
import hashlib
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QGraphicsItem, QGraphicsScene, QGraphicsView, QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QFont, QLinearGradient, QPainter,
    QCursor, QPixmap, QImage,
)
from PyQt6.QtCore import QByteArray, QBuffer
from loguru import logger

from src.ui.video_editor.config import (
    TRACK_HEIGHT_DEFAULT, TRACK_LABEL_WIDTH,
    TIMELINE_PIXELS_PER_SECOND as PPS, FFMPEG_PATH,
)
from src.ui.video_editor.styles import (
    THEME, TIMELINE_BG, TRACK_BG, TRACK_ALT_BG,
    CLIP_VIDEO_COLOR, CLIP_AUDIO_COLOR, CLIP_IMAGE_COLOR,
    CLIP_SUBTITLE_COLOR, PLAYHEAD_COLOR, SNAP_LINE_COLOR, SELECTION_COLOR,
)
from src.ui.video_editor.utils import format_time


# 缩略图缓存目录
_THUMB_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "video_editor" / "thumbs"
_THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 已加载的缩略图内存缓存 {clip_id: [QPixmap, ...]}
_THUMB_MEMORY: dict = {}
_THUMB_BYTES: dict = {}
# 正在生成中的 clip_id（避免重复生成）
_THUMB_PENDING: set = set()


# ====================================================================
# 跨线程缩略图通知（工作线程 emit → 主线程 slot，解决 QTimer 不触发）
# ====================================================================

class _ThumbnailReadySignal(QObject):
    ready = pyqtSignal(str, list)

_THUMB_READY = _ThumbnailReadySignal()



# ====================================================================
#  信号载体
# ====================================================================

class TimelineSignals(QObject):
    """时间轴信号聚合"""
    clip_clicked = pyqtSignal(str, int, int)       # clip_id, track_idx, clip_idx
    clip_double_clicked = pyqtSignal(str)           # clip_id
    clip_moved = pyqtSignal(str, float, float)      # clip_id, old_start, new_start
    playhead_moved = pyqtSignal(float)              # new_time
    clip_right_clicked = pyqtSignal(str, QPointF)   # clip_id, scene_pos
    clip_drag_finished = pyqtSignal(str, float)     # clip_id, final_timeline_start
    clip_trim_finished = pyqtSignal(str, float, float, float, float, float, float, float, float)
    # ^ clip_id, old_ts, new_ts, old_ss, new_ss, old_se, new_se, old_dur, new_dur
    context_menu_requested = pyqtSignal(str, int, QPointF)  # clip_id, track_idx, screen_pos


# ====================================================================
#  片段块 (ClipItem)
# ====================================================================

class ClipItem(QGraphicsRectItem):
    """时间轴上的一个片段块

    支持拖拽移动、拉伸首尾、右键菜单。
    颜色根据类型：视频=蓝 / 音频=绿 / 图片=橙。
    """

    HANDLE_WIDTH = 8         # 拖拽手柄宽度（首尾）
    MIN_VISUAL_WIDTH = 40    # 最小可见宽度（px，太小了看不到缩略图）
    SNAP_THRESHOLD = 8       # 吸附阈值（px）

    def __init__(self, clip_data: dict, parent=None):
        """
        clip_data 格式:
            id, type, track_index, timeline_start, source_start, source_end,
            duration, speed, source_path, name
        """
        self._data = clip_data
        self._dragging = False
        self._drag_start_pos = QPointF()
        self._drag_start_time = 0.0
        self._resizing = False
        self._resize_edge = ""  # "left" / "right"
        self._resize_old_ts = 0.0
        self._resize_old_ss = 0.0
        self._resize_old_se = 0.0
        self._resize_old_dur = 0.0
        self._snap_points: list[float] = []  # 外部注入的吸附点（秒）

        super().__init__(parent)

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # 设置光标
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # ---- 视频帧缩略图 ----
        self._thumbnails: list[QPixmap] = []
        self._thumb_loaded = False
        # 连接全局跨线程信号
        _THUMB_READY.ready.connect(self._on_thumbs_result, Qt.ConnectionType.QueuedConnection)
        # 视频类型才加载缩略图
        if self.clip_type == "video" and self.source_path:
            logger.info(f"[thumb] start: type={self.clip_type} path={self.source_path[:50]}...")
            self._load_thumbnails_async()
        else:
            logger.debug(f"跳过缩略图: type={self.clip_type} path={self.source_path[:30] if self.source_path else '无'}")

    def _load_thumbnails_async(self):
        """异步加载视频帧缩略图（后台 ffmpeg 抽帧）"""
        clip_id = self.clip_id
        # 已在内存缓存中
        if clip_id in _THUMB_MEMORY:
            self._thumbnails = _THUMB_MEMORY[clip_id]
            self._thumb_loaded = True
            self.update()
            return
        # 已有原始字节缓存
        if clip_id in _THUMB_BYTES:
            QTimer.singleShot(0, lambda: self._on_thumbs_result(_THUMB_BYTES[clip_id]))
            return
        # 正在生成中 -> 最多等待30秒后降级
        retry_count = getattr(self, '_thumb_retry', 0)
        if clip_id in _THUMB_PENDING:
            if retry_count < 10:
                self._thumb_retry = retry_count + 1
                QTimer.singleShot(3000, self._load_thumbnails_async)
            else:
                self._thumb_loaded = True  # 超时降级
                self.update()
            return

        self._thumb_retry = 0
        _THUMB_PENDING.add(clip_id)

        # 捕获值（避免线程闭包引用 self 导致野指针崩溃）
        _src_path = self.source_path
        _cid = clip_id

        def _do_extract():
            raw_frames = []
            try:
                raw_frames = _extract_video_thumbnails(_src_path, _cid)
                if raw_frames:
                    _THUMB_BYTES[_cid] = raw_frames
            except Exception as e:
                logger.warning(f"[thumb] extract error {_cid[:8]}: {e}")
            finally:
                _THUMB_PENDING.discard(_cid)
                # 用 pyqtSignal 跨线程通知（QTimer 在工作线程不触发！）
                _THUMB_READY.ready.emit(_cid, raw_frames)

        threading.Thread(target=_do_extract, daemon=True).start()

    def _on_thumbs_result(self, raw_frames: list):
        """缩略图就绪后更新显示（主线程，创建 QPixmap）"""
        clip_id = self.clip_id
        if raw_frames:
            pixmaps = []
            for raw in raw_frames:
                pix = QPixmap()
                if pix.loadFromData(raw):
                    pixmaps.append(pix)
            if pixmaps:
                _THUMB_MEMORY[clip_id] = pixmaps
                self._thumbnails = pixmaps
        self._thumb_loaded = True
        self.update()

    # ---- 属性 ----

    @property
    def clip_id(self) -> str:
        return self._data.get("id", "")

    @property
    def clip_type(self) -> str:
        return self._data.get("type", "video")

    @property
    def track_index(self) -> int:
        return self._data.get("track_index", 0)

    @track_index.setter
    def track_index(self, v: int):
        self._data["track_index"] = v

    @property
    def timeline_start(self) -> float:
        return self._data.get("timeline_start", 0.0)

    @timeline_start.setter
    def timeline_start(self, v: float):
        self._data["timeline_start"] = max(0, v)

    @property
    def duration(self) -> float:
        return self._data.get("duration", 0.0)

    @property
    def source_start(self) -> float:
        return self._data.get("source_start", 0.0)

    @property
    def source_end(self) -> float:
        return self._data.get("source_end", 0.0)

    @property
    def clip_name(self) -> str:
        return self._data.get("name", "?")

    @property
    def source_path(self) -> str:
        return self._data.get("source_path", "")

    @property
    def speed(self) -> float:
        return self._data.get("speed", 1.0)

    def set_snap_points(self, points: list[float]):
        """设置吸附参考点（秒）"""
        self._snap_points = list(points) if points else []

    # ---- 绘制 ----

    def paint(self, painter: QPainter, option, widget=None):
        """自定义绘制带渐变的片段块"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        is_selected = self.isSelected()

        # 类型颜色
        color_map = {
            "video": CLIP_VIDEO_COLOR,
            "audio": CLIP_AUDIO_COLOR,
            "image": CLIP_IMAGE_COLOR,
        }
        base_color = QColor(color_map.get(self.clip_type, CLIP_VIDEO_COLOR))

        # 渐变背景
        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        grad.setColorAt(0, base_color.lighter(130))
        grad.setColorAt(1, base_color.darker(120))
        painter.setBrush(QBrush(grad))

        # 边框
        if is_selected:
            pen = QPen(QColor(THEME["accent"]), 2)
        else:
            pen = QPen(base_color.darker(150), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)

        # ---- 视频帧缩略图 ----
        if self.clip_type == "video":
            if self._thumb_loaded and self._thumbnails:
                # 缩略图已就绪：绘制帧图（全高、紧密排列、覆盖整个 clip）
                painter.save()
                clip_path_rect = rect.adjusted(1, 1, -1, -1)
                painter.setClipRect(clip_path_rect)
                n = len(self._thumbnails)
                avail_w = rect.width() - 4
                if n > 0 and avail_w > 4:
                    thumb_w = max(avail_w / n, 4)  # 均分宽度，最小4px
                    thumb_h = rect.height() - 4
                    x = 2
                    for pix in self._thumbnails:
                        if x >= rect.width() - 2:
                            break
                        w = min(thumb_w, rect.width() - x - 2)
                        scaled = pix.scaled(int(w), int(thumb_h),
                                            Qt.AspectRatioMode.IgnoreAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
                        painter.drawPixmap(int(x), int(rect.top() + 2), scaled)
                        x += int(thumb_w)
                painter.restore()
            elif not self._thumb_loaded:
                # 缩略图加载中：显示加载指示
                painter.save()
                painter.setPen(QColor(255, 255, 255, 80))
                font = QFont("Microsoft YaHei", 7)
                painter.setFont(font)
                painter.drawText(rect.adjusted(10, 0, -10, -20),
                                 Qt.AlignmentFlag.AlignCenter, "···")
                painter.restore()

            else:
                # 加载完成但无缩略图（降级显示）
                painter.save()
                painter.setPen(QColor(255, 255, 255, 60))
                font = QFont("Microsoft YaHei", 11)
                painter.setFont(font)
                painter.drawText(rect.adjusted(10, 4, -10, -20),
                                 Qt.AlignmentFlag.AlignCenter, "🎬")
                painter.restore()

        # 文本（半透明背景上）
        if rect.width() > 30:
            # 半透明背景条让文字清晰
            painter.fillRect(rect.adjusted(1, rect.height() - 18, -1, -1),
                             QColor(0, 0, 0, 120))
            painter.setPen(QColor("#fff"))
            font = QFont("Microsoft YaHei", 8)
            painter.setFont(font)
            name_rect = rect.adjusted(6, rect.height() - 18, -6, -1)
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             self.clip_name[:25])

            # 时长标注（右上角）
            dur_rect = rect.adjusted(rect.width() - 60, 2, -4, 16)
            painter.fillRect(dur_rect, QColor(0, 0, 0, 120))
            painter.setPen(QColor(255, 255, 255, 200))
            font2 = QFont("Microsoft YaHei", 7)
            painter.setFont(font2)
            painter.drawText(dur_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             format_time(self.duration))

    # ---- 鼠标交互 ----

    def hoverMoveEvent(self, event):
        """鼠标悬停判断是否在边缘（用于拖拽拉伸）"""
        pos = event.pos()
        if pos.x() < self.HANDLE_WIDTH:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self._resize_edge = "left"
        elif pos.x() > self.rect().width() - self.HANDLE_WIDTH:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self._resize_edge = "right"
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._resize_edge = ""
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._resize_edge:
                self._resizing = True
                self._drag_start_pos = event.scenePos()
                self._drag_start_time = self.timeline_start
                self._resize_old_ts = self.timeline_start
                self._resize_old_ss = self.source_start
                self._resize_old_se = self.source_end
                self._resize_old_dur = self.duration
            else:
                self._dragging = True
                self._drag_start_pos = event.scenePos()
                self._drag_start_time = self.timeline_start
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键 → 通知父级显示上下文菜单
            self.setSelected(True)
            scene = self.scene()
            if scene:
                views = scene.views()
                if views:
                    screen_pos = views[0].mapToGlobal(
                        views[0].mapFromScene(event.scenePos())
                    )
                    # 通过 scene 的自定义属性传递
                    if hasattr(scene, 'context_menu_callback'):
                        scene.context_menu_callback(self.clip_id, self.track_index, screen_pos)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.scenePos() - self._drag_start_pos
            raw_start = self._drag_start_time + delta.x() / PPS
            new_start = max(0, raw_start)

            # ---- 吸附 ----
            snapped = False
            snap_threshold = self.SNAP_THRESHOLD / PPS  # 转换为秒
            new_start_px = new_start * PPS

            for sp in self._snap_points:
                sp_px = sp * PPS
                if abs(new_start_px - sp_px) < self.SNAP_THRESHOLD:
                    new_start = sp
                    snapped = True
                    break

            # 也检查片段两端吸附
            clip_end_px = (new_start + self.duration) * PPS
            for sp in self._snap_points:
                sp_px = sp * PPS
                if abs(clip_end_px - sp_px) < self.SNAP_THRESHOLD:
                    new_start = sp - self.duration
                    snapped = True
                    break

            self.timeline_start = new_start
            self.setPos(self.timeline_start * PPS, 0)

            # 更新吸附指示线（通过 scene 获取）
            if snapped:
                scene = self.scene()
                if scene and hasattr(scene, 'show_snap_line'):
                    scene.show_snap_line(new_start * PPS)
        elif self._resizing:
            delta = event.scenePos() - self._drag_start_pos
            if self._resize_edge == "right":
                new_dur = max(0.1, self.duration + delta.x() / PPS)
                self._data["duration"] = new_dur
                self._data["source_end"] = self.source_start + new_dur
                self.setRect(0, 0, new_dur * PPS, self.rect().height())
            elif self._resize_edge == "left":
                new_start = self._drag_start_time + delta.x() / PPS
                dur_delta = self._drag_start_time - new_start
                new_dur = max(0.1, self.duration + dur_delta)
                if new_dur > 0.1:
                    src_delta = self._drag_start_time - new_start
                    self.timeline_start = new_start
                    self._data["duration"] = new_dur
                    self._data["source_start"] = max(0, self._resize_old_ss + src_delta)
                    self.setPos(self.timeline_start * PPS, 0)
                    self.setRect(0, 0, new_dur * PPS, self.rect().height())

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            # 通知拖拽完成
            scene = self.scene()
            if scene and hasattr(scene, 'clip_drag_finished_callback'):
                scene.clip_drag_finished_callback(self.clip_id, self.timeline_start)
            # 隐藏吸附线
            if scene and hasattr(scene, 'hide_snap_line'):
                scene.hide_snap_line()
        if self._resizing:
            scene = self.scene()
            if scene and hasattr(scene, "clip_trim_finished_callback"):
                scene.clip_trim_finished_callback(
                    self.clip_id,
                    self._resize_old_ts, self.timeline_start,
                    self._resize_old_ss, self.source_start,
                    self._resize_old_se, self.source_end,
                    self._resize_old_dur, self.duration,
                )
        self._dragging = False
        self._resizing = False
        super().mouseReleaseEvent(event)


# ====================================================================
#  播放头 (PlayheadLine)
# ====================================================================

class PlayheadLine(QGraphicsLineItem):
    """红色播放头竖线"""

    def __init__(self, height: float, parent=None):
        super().__init__(parent)
        self._height = height
        self.setPen(QPen(QColor(PLAYHEAD_COLOR), 2))
        self.setZValue(100)
        self.setLine(0, 0, 0, height)
        # 三角形顶部指示器
        self._triangle = QGraphicsRectItem(self)
        tri_w = 10
        self._triangle.setRect(-tri_w / 2, -tri_w, tri_w, tri_w)
        self._triangle.setBrush(QBrush(QColor(PLAYHEAD_COLOR)))
        self._triangle.setPen(QPen(Qt.PenStyle.NoPen))


# ====================================================================
#  时间标尺 (TimeRuler)
# ====================================================================

class TimeRuler(QGraphicsRectItem):
    """时间轴顶部的时间标尺"""

    HEIGHT = 24

    def __init__(self, total_width: float, parent=None):
        super().__init__(parent)
        self._total_width = total_width
        self.setRect(0, 0, total_width, self.HEIGHT)
        self.setBrush(QBrush(QColor(TIMELINE_BG)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(90)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)

        rect = self.rect()
        painter.setPen(QPen(QColor(THEME["text_muted"]), 1))

        # 刻度线
        total_sec = rect.width() / PPS
        interval = self._tick_interval(total_sec)

        t = 0.0
        while t <= total_sec:
            x = t * PPS
            if x > rect.width():
                break
            painter.drawLine(QPointF(x, rect.bottom() - 10), QPointF(x, rect.bottom()))

            # 时间标签
            painter.setPen(QColor(THEME["text_secondary"]))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(
                QRectF(x - 30, 0, 60, rect.height() - 12),
                Qt.AlignmentFlag.AlignCenter,
                format_time(t),
            )
            painter.setPen(QPen(QColor(THEME["text_muted"]), 1))
            t += interval

    @staticmethod
    def _tick_interval(total_sec: float) -> float:
        """根据总时长选择合适的刻度间隔"""
        if total_sec <= 10:
            return 1
        elif total_sec <= 30:
            return 5
        elif total_sec <= 120:
            return 10
        elif total_sec <= 600:
            return 30
        else:
            return 60


# ====================================================================
#  轨道背景 (TrackBackground)
# ====================================================================

class TrackBackground(QGraphicsRectItem):
    """单条轨道背景"""

    def __init__(self, track_index: int, track_type: str,
                 width: float, y: float, parent=None):
        super().__init__(parent)
        self._track_index = track_index
        self._track_type = track_type
        self._total_width = width
        self._track_y = y

        self.setRect(0, y, width, TRACK_HEIGHT_DEFAULT)
        alt = track_index % 2 == 1
        bg = QColor(TRACK_ALT_BG) if alt else QColor(TRACK_BG)
        self.setBrush(QBrush(bg))
        self.setPen(QPen(QColor(THEME["border"]), 1))
        self.setZValue(10)

        # 轨道标签
        icons = {"video": "🎬", "audio": "🎵", "subtitle": "💬"}
        label = QGraphicsTextItem(f"{icons.get(track_type, '📄')} {track_type}", self)
        label.setDefaultTextColor(QColor(THEME["text_muted"]))
        label.setFont(QFont("Microsoft YaHei", 9))
        label.setPos(4, y + TRACK_HEIGHT_DEFAULT / 2 - 10)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        # 绘制垂直网格线（与时间标尺对齐）
        rect = self.rect()
        total_sec = self._total_width / PPS
        interval = self._tick_interval(total_sec)
        painter.setPen(QPen(QColor(THEME["border"]), 1, Qt.PenStyle.DotLine))
        t = 0.0
        while t <= total_sec:
            x = t * PPS
            if x > self._total_width:
                break
            painter.drawLine(
                int(x), int(rect.top()),
                int(x), int(rect.bottom())
            )
            t += interval

    @staticmethod
    def _tick_interval(total_sec: float) -> float:
        if total_sec <= 10:
            return 1
        elif total_sec <= 30:
            return 5
        elif total_sec <= 120:
            return 10
        elif total_sec <= 600:
            return 30
        else:
            return 60


# ====================================================================
#  吸附指示线
# ====================================================================

class SnapIndicator(QGraphicsLineItem):
    """拖拽时的吸附参考线"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPen(QPen(QColor(SNAP_LINE_COLOR), 1, Qt.PenStyle.DashLine))
        self.setZValue(95)
        self.setVisible(False)

    def show_at(self, x: float, y_top: float, height: float):
        self.setLine(x, y_top, x, y_top + height)
        self.setVisible(True)

    def hide_indicator(self):
        self.setVisible(False)


# ====================================================================
#  视频帧缩略图提取（模块级函数）
# ====================================================================

def _extract_video_thumbnails(video_path: str, clip_id: str, max_frames: int = 30) -> list[bytes]:
    """用 ffmpeg 从视频中提取 N 帧 JPEG 字节（线程安全，不触碰 Qt GUI）"""
    logger.info(f"[thumb] start: clip={clip_id[:8]} path={video_path[:80]}")

    if not FFMPEG_PATH.exists():
        logger.warning(f"[thumb] ffmpeg not found: {FFMPEG_PATH}")
        return []

    if not os.path.exists(video_path):
        logger.warning(f"[thumb] video not found: {video_path}")
        return []

    # 磁盘缓存 key
    try:
        stat = os.stat(video_path)
        cache_key = hashlib.md5(
            f"{video_path}_{stat.st_size}_{int(stat.st_mtime)}".encode()
        ).hexdigest()[:16]
    except Exception:
        cache_key = hashlib.md5(video_path.encode()).hexdigest()[:16]

    # 检查磁盘缓存
    cache_file = _THUMB_CACHE_DIR / f"{cache_key}.dat"
    if cache_file.exists():
        raw_frames = []
        try:
            data = cache_file.read_bytes()
            i = 0
            while i + 4 <= len(data):
                length = int.from_bytes(data[i:i+4], 'little')
                i += 4
                if i + length > len(data):
                    break
                raw_frames.append(data[i:i+length])
                i += length
        except Exception as e:
            logger.warning(f"[thumb] cache read error: {e}")
        if raw_frames:
            logger.info(f"[thumb] cache hit: {len(raw_frames)} frames")
            return raw_frames

    # 用 ffmpeg 抽帧
    import tempfile
    tmp_dir = Path(tempfile.gettempdir()) / f"thumbs_{clip_id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 获取视频时长
    duration = 10.0
    try:
        result = subprocess.run(
            [str(FFMPEG_PATH), "-i", video_path],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10
        )
        for line in (result.stderr or "").split('\n'):
            if 'Duration' in line:
                parts = line.split('Duration:')[1].split(',')[0].strip().split(':')
                duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                break
        if duration <= 0:
            duration = 10.0
        logger.info(f"[thumb] duration={duration:.1f}s")
    except Exception as e:
        logger.warning(f"[thumb] duration parse failed: {e}")

    # 均匀采样 N 帧（-ss 在 -i 前加速 seek）
    thumbs = []
    for i in range(max_frames):
        t = duration * (i + 0.5) / max_frames
        out_file = tmp_dir / f"thumb_{i:03d}.jpg"
        try:
            subprocess.run(
                [str(FFMPEG_PATH), "-y", "-ss", str(t), "-i", video_path,
                 "-vframes", "1", "-q:v", "3",
                 "-vf", "scale=320:-1",
                 str(out_file)],
                capture_output=True, timeout=10
            )
            if out_file.exists() and out_file.stat().st_size > 100:
                raw_bytes = out_file.read_bytes()
                if len(raw_bytes) > 100:
                    thumbs.append(raw_bytes)
                out_file.unlink()
        except Exception as e:
            logger.warning(f"[thumb] frame {i} failed t={t:.1f}: {e}")

    # 清理临时目录
    try:
        tmp_dir.rmdir()
    except Exception:
        pass

    # 写入磁盘缓存
    if thumbs:
        try:
            buffer = bytearray()
            for raw in thumbs:
                buffer.extend(len(raw).to_bytes(4, 'little'))
                buffer.extend(raw)
            cache_file.write_bytes(bytes(buffer))
        except Exception as e:
            logger.warning(f"[thumb] cache write error: {e}")

    logger.info(f"[thumb] done: {len(thumbs)} frames, clip={clip_id[:8]}")
    return thumbs
