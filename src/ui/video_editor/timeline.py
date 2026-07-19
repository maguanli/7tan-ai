"""
视频剪辑器 — 时间轴组件

基于 QGraphicsView/QGraphicsScene，支持多轨道显示、片段拖拽、播放头、缩放。

Phase 2: 多轨道显示 + 片段拖拽 + 播放头 + 时间标尺 + 缩放
"""

from typing import Optional

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QWheelEvent, QMouseEvent, QKeyEvent, QPainter,
)

from loguru import logger

from src.ui.video_editor.config import (
    TRACK_HEIGHT_DEFAULT, TRACK_LABEL_WIDTH,
    TIMELINE_PIXELS_PER_SECOND as PPS,
    TIMELINE_MIN_ZOOM, TIMELINE_MAX_ZOOM,
    CLIP_MIN_DURATION, IMAGE_DEFAULT_DURATION,
    DEFAULT_DURATION,
)
from src.ui.video_editor.styles import TIMELINE_BG, THEME
from src.ui.video_editor.timeline_items import (
    ClipItem, PlayheadLine, TimeRuler, TrackBackground,
    SnapIndicator, TimelineSignals,
)
from src.ui.video_editor.data_models import Clip, Track, Project, SubtitleClip
from src.ui.video_editor.utils import generate_clip_id, format_time


class TimelineView(QGraphicsView):
    """时间轴主视图

    信号：
        clip_selected(clip_id, track_idx, clip_idx)
        playhead_moved(float)     — 播放头位置（秒）
        clip_added_to_timeline(dict) — 素材拖入时间轴
    """

    clip_selected = pyqtSignal(str, int, int)
    playhead_moved = pyqtSignal(float)
    clip_added_to_timeline = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 场景
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # 数据
        self._project: Optional[Project] = None
        self._clip_items: dict[str, ClipItem] = {}  # clip_id → ClipItem
        self._track_count: int = 4  # 默认：1视频 + 2音频 + 1字幕
        self._track_types = ["video", "audio", "audio", "subtitle"]
        self._zoom: float = 1.0
        self._playhead_time: float = 0.0

        # 子元素
        self._playhead: Optional[PlayheadLine] = None
        self._ruler: Optional[TimeRuler] = None
        self._snap: Optional[SnapIndicator] = None
        self._track_bgs: list[TrackBackground] = []

        # 拖拽状态
        self._dragging_playhead = False

        # 信号
        self._signals = TimelineSignals()
        self._signals.clip_moved.connect(self._on_clip_moved)

        # 视图设置
        self._setup_view()
        self._build_scene()

    # ==================================================================
    #  视图设置
    # ==================================================================

    def _setup_view(self):
        """配置 QGraphicsView 参数"""
        self.setStyleSheet(f"background-color:{TIMELINE_BG}; border:none;")
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    # ==================================================================
    #  场景构建
    # ==================================================================

    def _build_scene(self):
        """构建初始场景（标尺 + 轨道背景 + 播放头）"""
        self._scene.clear()
        self._clip_items.clear()
        self._track_bgs.clear()

        total_width = DEFAULT_DURATION * PPS
        ruler_height = TimeRuler.HEIGHT
        total_height = ruler_height + self._track_count * TRACK_HEIGHT_DEFAULT

        # 场景大小
        self._scene.setSceneRect(0, 0, total_width, total_height)

        # 时间标尺
        self._ruler = TimeRuler(total_width)
        self._scene.addItem(self._ruler)

        # 轨道背景
        for i in range(self._track_count):
            y = ruler_height + i * TRACK_HEIGHT_DEFAULT
            track_type = self._track_types[i] if i < len(self._track_types) else "video"
            bg = TrackBackground(i, track_type, total_width, y)
            self._scene.addItem(bg)
            self._track_bgs.append(bg)

        # 播放头
        ph_height = total_height - ruler_height
        self._playhead = PlayheadLine(ph_height)
        self._playhead.setPos(0, ruler_height)
        self._scene.addItem(self._playhead)

        # 吸附线
        self._snap = SnapIndicator()
        self._scene.addItem(self._snap)

    def _rebuild_scene(self):
        """根据项目数据重建场景"""
        self._build_scene()

        if not self._project:
            return

        ruler_height = TimeRuler.HEIGHT

        for ti, track in enumerate(self._project.tracks):
            y = ruler_height + ti * TRACK_HEIGHT_DEFAULT
            for ci, clip in enumerate(track.clips):
                if isinstance(clip, Clip):
                    self._add_clip_item(clip, y)
                elif isinstance(clip, SubtitleClip):
                    self._add_subtitle_item(clip, y)

    # ==================================================================
    #  公开 API
    # ==================================================================

    def set_project(self, project: Project):
        """绑定项目数据"""
        self._project = project
        self._rebuild_scene()

    def set_playhead(self, time_sec: float):
        """移动播放头到指定时间"""
        self._playhead_time = max(0, time_sec)
        ruler_height = TimeRuler.HEIGHT
        x = self._playhead_time * PPS
        self._playhead.setPos(x, ruler_height)
        # 自动滚动视图跟随播放头
        self.centerOn(x, self._playhead.pos().y())

    def get_playhead_time(self) -> float:
        return self._playhead_time

    def add_clip(self, media_info: dict, track_index: int = 0,
                 timeline_start: float = None) -> Optional[str]:
        """添加片段到时间轴

        Args:
            media_info: 素材信息（含 path/type/duration/name）
            track_index: 目标轨道
            timeline_start: 起始时间，默认=播放头位置

        Returns:
            clip_id 或 None
        """
        if not self._project:
            return None

        # 确保轨道存在
        while len(self._project.tracks) <= track_index:
            t_type = self._track_types[len(self._project.tracks)] \
                if len(self._project.tracks) < len(self._track_types) else "video"
            self._project.tracks.append(Track(type=t_type, clips=[]))

        track = self._project.tracks[track_index]

        # 默认插入位置 = 播放头
        if timeline_start is None:
            timeline_start = self._playhead_time

        # 智能选择轨道：音频默认放音频轨
        mt = media_info.get("type", "video")
        if mt == "audio" and track_index == 0:
            track_index = 1  # 第一个音频轨
            if len(self._project.tracks) <= track_index:
                self._project.tracks.append(Track(type="audio", clips=[]))
            track = self._project.tracks[track_index]

        dur = media_info.get("duration", IMAGE_DEFAULT_DURATION)
        if mt == "image":
            dur = IMAGE_DEFAULT_DURATION

        cid = generate_clip_id()
        clip = Clip(
            id=cid,
            source_path=media_info["path"],
            type=mt,
            track_index=track_index,
            timeline_start=timeline_start,
            source_start=0.0,
            source_end=dur,
            duration=dur,
            speed=1.0,
        )

        track.clips.append(clip)

        # 添加到场景
        ruler_height = TimeRuler.HEIGHT
        y = ruler_height + track_index * TRACK_HEIGHT_DEFAULT
        self._add_clip_item(clip, y)

        # 更新项目时长
        self._update_project_duration()

        logger.info(f"添加片段: {clip.id} → 轨道{track_index} @{format_time(timeline_start)}")
        return cid

    def remove_clip(self, clip_id: str) -> bool:
        """移除片段"""
        if not self._project:
            return False

        for track in self._project.tracks:
            for clip in track.clips:
                if isinstance(clip, Clip) and clip.id == clip_id:
                    track.clips.remove(clip)
                    # 从场景移除
                    if clip_id in self._clip_items:
                        item = self._clip_items.pop(clip_id)
                        self._scene.removeItem(item)
                    self._update_project_duration()
                    return True
        return False

    def zoom_in(self):
        """放大时间轴"""
        self._set_zoom(self._zoom * 1.25)

    def zoom_out(self):
        """缩小时间轴"""
        self._set_zoom(self._zoom / 1.25)

    def zoom_to_fit(self):
        """缩放至适合窗口"""
        if self._project:
            dur = self._project.duration or DEFAULT_DURATION
            view_width = self.viewport().width()
            new_pps = view_width / max(dur, 1)
            new_zoom = new_pps / 100  # 以 PPS=100 为基准
            self._set_zoom(new_zoom)

    # ==================================================================
    #  内部方法
    # ==================================================================

    def _add_clip_item(self, clip: Clip, y: float):
        """在场景中添加一个 ClipItem"""
        data = {
            "id": clip.id,
            "type": clip.type,
            "track_index": clip.track_index,
            "timeline_start": clip.timeline_start,
            "source_start": clip.source_start,
            "source_end": clip.source_end,
            "duration": clip.duration,
            "speed": clip.speed,
            "source_path": clip.source_path,
            "name": clip.source_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
        }

        width = max(clip.duration * PPS, ClipItem.MIN_VISUAL_WIDTH)
        h = TRACK_HEIGHT_DEFAULT - 4
        item = ClipItem(data)
        item.setRect(0, 2, width, h)
        item.setPos(clip.timeline_start * PPS, y)
        item.setZValue(50)

        self._scene.addItem(item)
        self._clip_items[clip.id] = item

    def _add_subtitle_item(self, sub: SubtitleClip, y: float):
        """添加字幕片段到场景"""
        data = {
            "id": sub.id,
            "type": "subtitle",
            "track_index": sub.track_index,
            "timeline_start": sub.start_time,
            "source_start": 0,
            "source_end": sub.end_time - sub.start_time,
            "duration": sub.end_time - sub.start_time,
            "speed": 1.0,
            "source_path": "",
            "name": sub.text[:30],
        }

        width = max(data["duration"] * PPS, ClipItem.MIN_VISUAL_WIDTH)
        h = TRACK_HEIGHT_DEFAULT - 4
        item = ClipItem(data)
        item.setRect(0, 2, width, h)
        item.setPos(sub.start_time * PPS, y)
        item.setZValue(50)

        self._scene.addItem(item)
        self._clip_items[sub.id] = item

    def _on_clip_moved(self, clip_id: str, old_start: float, new_start: float):
        """片段移动后同步数据模型"""
        if not self._project:
            return
        for track in self._project.tracks:
            for clip in track.clips:
                if isinstance(clip, Clip) and clip.id == clip_id:
                    clip.timeline_start = new_start
                    self._update_project_duration()
                    return

    def _update_project_duration(self):
        """更新项目总时长"""
        if not self._project:
            return
        max_end = 0.0
        for track in self._project.tracks:
            for clip in track.clips:
                if isinstance(clip, Clip):
                    end = clip.timeline_start + (clip.duration / max(clip.speed, 0.01))
                    max_end = max(max_end, end)
                elif isinstance(clip, SubtitleClip):
                    max_end = max(max_end, clip.end_time)
        self._project.duration = max(max_end, DEFAULT_DURATION)

        # 扩展场景
        total_width = self._project.duration * PPS * 1.5
        sr = self._scene.sceneRect()
        if total_width > sr.width():
            self._scene.setSceneRect(0, 0, total_width, sr.height())

    def _set_zoom(self, zoom: float):
        """设置缩放级别"""
        self._zoom = max(TIMELINE_MIN_ZOOM, min(TIMELINE_MAX_ZOOM, zoom))
        # 重设变换
        self.resetTransform()
        self.scale(self._zoom, 1.0)

    # ==================================================================
    #  事件处理
    # ==================================================================

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+滚轮缩放"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标点击：在标尺区拖拽播放头"""
        pos = self.mapToScene(event.pos())

        # 点击时间标尺 → 跳转播放头
        if pos.y() <= TimeRuler.HEIGHT:
            self._dragging_playhead = True
            new_time = pos.x() / PPS
            self.set_playhead(new_time)
            self.playhead_moved.emit(new_time)
            return

        # 常规选中
        item = self._scene.itemAt(pos, self.transform())
        if isinstance(item, ClipItem):
            self.clip_selected.emit(item.clip_id, item.track_index, 0)
        else:
            self._scene.clearSelection()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动：拖拽播放头"""
        if self._dragging_playhead:
            pos = self.mapToScene(event.pos())
            new_time = max(0, pos.x() / PPS)
            self.set_playhead(new_time)
            self.playhead_moved.emit(new_time)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging_playhead = False
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        """接受从素材库拖入"""
        if event.mimeData().hasFormat("application/x-media-info"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """从素材库拖入片段到时间轴"""
        if event.mimeData().hasFormat("application/x-media-info"):
            import json
            data = json.loads(event.mimeData().data("application/x-media-info").data().decode())
            pos = self.mapToScene(event.position().toPoint())
            # 判断落在哪个轨道
            ruler_height = TimeRuler.HEIGHT
            track_idx = int((pos.y() - ruler_height) / TRACK_HEIGHT_DEFAULT)
            track_idx = max(0, min(track_idx, self._track_count - 1))
            time_start = max(0, pos.x() / PPS)

            self.add_clip(data, track_idx, time_start)
            self.clip_added_to_timeline.emit(data)
            event.acceptProposedAction()
        else:
            event.ignore()
