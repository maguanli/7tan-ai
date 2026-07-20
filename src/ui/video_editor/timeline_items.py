"""
视频剪辑器 — 时间轴 QGraphicsScene 元素

包含片段块、轨道背景、时间标尺、播放头等可绘制元素。

Phase 3: 右键菜单支持 + 吸附增强
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QGraphicsItem, QGraphicsScene, QGraphicsView, QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QFont, QLinearGradient, QPainter,
    QCursor, QPixmap,
)

from src.ui.video_editor.config import (
    TRACK_HEIGHT_DEFAULT, TRACK_LABEL_WIDTH,
    TIMELINE_PIXELS_PER_SECOND as PPS,
)
from src.ui.video_editor.styles import (
    THEME, TIMELINE_BG, TRACK_BG, TRACK_ALT_BG,
    CLIP_VIDEO_COLOR, CLIP_AUDIO_COLOR, CLIP_IMAGE_COLOR,
    CLIP_SUBTITLE_COLOR, PLAYHEAD_COLOR, SNAP_LINE_COLOR, SELECTION_COLOR,
)
from src.ui.video_editor.utils import format_time


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
    MIN_VISUAL_WIDTH = 12    # 最小可见宽度（px）
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
        self._snap_points: list[float] = []  # 外部注入的吸附点（秒）

        super().__init__(parent)

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # 设置光标
        self.setCursor(Qt.CursorShape.OpenHandCursor)

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
    def speed(self) -> float:
        return self._data.get("speed", 1.0)

    def set_snap_points(self, points: list[float]):
        """设置吸附参考点（秒）"""
        self._snap_points = list(points) if points else []

    @property
    def source_path(self) -> str:
        return self._data.get("source_path", "")

    def _get_thumb(self) -> Optional[QPixmap]:
        """从 clip data 中的 thumb_path 加载缩略图"""
        thumb_path = self._data.get("thumb_path", "")
        if thumb_path:
            pix = QPixmap(thumb_path)
            if not pix.isNull():
                return pix
        return None

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

        # 视频帧缩略图 — 暂时禁用排查崩溃
        if False and self.clip_type == "video" and rect.width() > 50:
            thumb = self._get_thumb()
            if thumb is not None and not thumb.isNull():
                # 裁剪绘制
                r = rect.adjusted(2, 2, -2, -2)
                painter.save()
                painter.setClipRect(r)
                tw = r.width()
                th = r.height()
                scaled = thumb.scaled(int(tw), int(th),
                                      Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
                sx = (scaled.width() - tw) // 2
                sy = (scaled.height() - th) // 2
                painter.drawPixmap(int(r.x()) - sx, int(r.y()) - sy, scaled)
                painter.restore()

        # 文本
        if rect.width() > 30:
            painter.setPen(QColor("#fff"))
            font = QFont("Microsoft YaHei", 9)
            painter.setFont(font)
            name_rect = rect.adjusted(6, 2, -6, -(rect.height() / 2))
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             self.clip_name[:20])

            # 时长标注
            dur_rect = rect.adjusted(6, rect.height() / 2, -6, -2)
            painter.setPen(QColor(255, 255, 255, 180))
            font2 = QFont("Microsoft YaHei", 8)
            painter.setFont(font2)
            painter.drawText(dur_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
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
                self.setRect(0, 0, new_dur * PPS, self.rect().height())
            elif self._resize_edge == "left":
                new_start = self._drag_start_time + delta.x() / PPS
                dur_delta = self._drag_start_time - new_start
                new_dur = max(0.1, self.duration + dur_delta)
                if new_dur > 0.1:
                    self.timeline_start = new_start
                    self._data["duration"] = new_dur
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

        self.setRect(0, y, width, TRACK_HEIGHT_DEFAULT)
        alt = track_index % 2 == 1
        bg = QColor(TRACK_ALT_BG) if alt else QColor(TRACK_BG)
        self.setBrush(QBrush(bg))
        self.setPen(QPen(QColor(THEME["border"]), 1))

        # 轨道标签
        icons = {"video": "🎬", "audio": "🎵", "subtitle": "💬"}
        label = QGraphicsTextItem(f"{icons.get(track_type, '📄')} {track_type}", self)
        label.setDefaultTextColor(QColor(THEME["text_muted"]))
        label.setFont(QFont("Microsoft YaHei", 9))
        label.setPos(4, y + TRACK_HEIGHT_DEFAULT / 2 - 10)


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
