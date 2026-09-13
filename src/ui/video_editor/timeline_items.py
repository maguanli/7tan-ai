"""
视频剪辑器 — 时间轴 QGraphicsScene 元素

包含片段块、轨道背景、时间标尺、播放头等可绘制元素。

Phase 3: 右键菜单支持 + 吸附增强
"""

import hashlib
import subprocess
import threading
from pathlib import Path
from typing import Optional

from loguru import logger

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject, QThread
from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QGraphicsItem, QGraphicsScene, QGraphicsView, QMenu, QApplication,
)
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QFont, QLinearGradient, QPainter,
    QCursor, QPixmap, QPixmap,
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
#  缩略图信号（跨线程）
# ====================================================================

class _ThumbSignals(QObject):
    """缩略图就绪信号 — 跨线程安全"""
    ready = pyqtSignal(str, list)  # clip_id, [raw_jpeg_bytes, ...]

_THUMB_READY = _ThumbSignals()

# global callback registry (fixes multi-clip signal race)
_thumb_callbacks = {}

def _global_thumb_dispatcher(clip_id, raw_frames):
    cb = _thumb_callbacks.pop(clip_id, None)
    if cb:
        cb(clip_id, raw_frames)

_THUMB_READY.ready.connect(_global_thumb_dispatcher)


# ====================================================================
#  缩略图提取工作线程
# ====================================================================

THUMB_COUNT = 15
THUMB_SAMPLE_W = 360
THUMB_CACHE_DIR = Path("data/video_editor/thumbs")
THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
THUMB_MAX_CONCURRENT = 2
_extract_sem = threading.Semaphore(THUMB_MAX_CONCURRENT)
_extract_queue = []
_extract_queue_lock = threading.Lock()


def _thumb_cache_key(src_path, source_start, source_end):
    raw = f"{src_path}|{source_start:.3f}|{source_end:.3f}"
    return hashlib.md5(raw.encode()).hexdigest()


def _thumb_load_cache(cache_key):
    cache_file = THUMB_CACHE_DIR / f"{cache_key}.thumb"
    if not cache_file.exists():
        return []
    try:
        data = cache_file.read_bytes()
        if len(data) < 4:
            return []
        nframes = int.from_bytes(data[:4], 'big')
        if nframes <= 0 or nframes > 100:
            return []
        frames = []
        offset = 4
        for _ in range(nframes):
            if offset + 4 > len(data):
                break
            fsize = int.from_bytes(data[offset:offset + 4], 'big')
            offset += 4
            if fsize <= 0 or offset + fsize > len(data):
                break
            frames.append(data[offset:offset + fsize])
            offset += fsize
        return frames if len(frames) == nframes else []
    except Exception:
        return []


def _thumb_save_cache(cache_key, frames):
    if not frames:
        return
    cache_file = THUMB_CACHE_DIR / f"{cache_key}.thumb"
    try:
        parts = [len(frames).to_bytes(4, 'big')]
        for f in frames:
            parts.append(len(f).to_bytes(4, 'big'))
            parts.append(f)
        cache_file.write_bytes(b''.join(parts))
    except Exception:
        pass


def _process_queue():
    while True:
        with _extract_queue_lock:
            if not _extract_queue:
                return
            task = _extract_queue.pop(0)
        if _extract_sem.acquire(blocking=False):
            cid, sp, dur, ss, se = task
            threading.Thread(
                target=_extract_thumbs_worker,
                args=(cid, sp, dur, ss, se),
                daemon=True,
            ).start()
        else:
            with _extract_queue_lock:
                _extract_queue.insert(0, task)
            return


def _enqueue_extraction(clip_id, src_path, duration, source_start, source_end):
    with _extract_queue_lock:
        for item in _extract_queue:
            if item[0] == clip_id:
                return
        _extract_queue.append((clip_id, src_path, duration, source_start, source_end))
    _process_queue()


def _extract_thumbs_worker(clip_id: str, src_path: str, duration: float,
                           source_start: float, source_end: float):
    """在后台线程中用 ffmpeg 抽帧，完成后通过信号通知主线程。

    策略：用 ffmpeg -vf fps=... 均匀采样，输出为 pipe 中的 JPEG 字节。
    完全不使用 QPixmap/QImage（Qt GUI 对象禁止跨线程）。
    """
    from src.ui.video_editor.config import FFMPEG_PATH

    raw_frames: list[bytes] = []

    # cache check + early validation
    used_duration = source_end - source_start if (source_end - source_start) > 0 else duration
    if used_duration <= 0:
        _THUMB_READY.ready.emit(clip_id, raw_frames)
        _extract_sem.release()
        _process_queue()
        return

    # disk cache hit
    ck = _thumb_cache_key(src_path, source_start, source_end)
    cached = _thumb_load_cache(ck)
    if cached:
        _THUMB_READY.ready.emit(clip_id, cached)
        _extract_sem.release()
        _process_queue()
        return

    if not FFMPEG_PATH or not FFMPEG_PATH.exists():
        _THUMB_READY.ready.emit(clip_id, raw_frames)
        _extract_sem.release()
        _process_queue()
        return
    if not src_path or not Path(src_path).exists():
        _THUMB_READY.ready.emit(clip_id, raw_frames)
        _extract_sem.release()
        _process_queue()
        return

    count = min(THUMB_COUNT, max(3, int(used_duration * 2)))
    fps = count / max(used_duration, 0.1)

    proc = None
    try:
        # ffmpeg 命令：从 source_start 开始，取 used_duration 时长，fps 帧率
        cmd = [
            str(FFMPEG_PATH),
            "-ss", str(source_start),
            "-t", str(used_duration),
            "-i", src_path,
            "-vf", f"fps={fps},scale={THUMB_SAMPLE_W}:-1",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-q:v", "5",
            "-v", "error",
            "-",
        ]
        logger.info(f"[thumb] ffmpeg start: {clip_id[:8]} src={Path(src_path).name} dur={used_duration:.1f}s")
        proc = subprocess.run(
            cmd, capture_output=True, timeout=15,
        )
        if proc.returncode == 0 and proc.stdout:
            # 按 JPEG SOI marker (0xFF 0xD8) 分割
            data = proc.stdout
            jpeg_marker = b'\xff\xd8'
            parts = data.split(jpeg_marker)
            for part in parts[1:]:  # 第一个是空的（第一个 marker 之前）
                frame = jpeg_marker + part
                raw_frames.append(frame)
            # 限制数量
            if len(raw_frames) > THUMB_COUNT:
                step = len(raw_frames) / THUMB_COUNT
                raw_frames = [raw_frames[int(i * step)] for i in range(THUMB_COUNT)]
    except subprocess.TimeoutExpired:
        logger.warning(f"[thumb] ffmpeg TIMEOUT: {clip_id[:8]} src={Path(src_path).name}")
    except Exception as e:
        logger.warning(f"[thumb] ffmpeg failed: {clip_id[:8]} src={Path(src_path).name} err={e}")

    if raw_frames:
        logger.info(f"[thumb] ffmpeg done: {clip_id[:8]} frames={len(raw_frames)}")
    else:
        stderr_tail = (proc.stderr or b"").decode(errors="replace")[-200:] if proc and proc.stderr else "(no stderr)"
        logger.warning(f"[thumb] ffmpeg produced no frames: {clip_id[:8]} src={Path(src_path).name} rc={proc.returncode if proc else '?'} stderr={stderr_tail}")

    # save to disk cache
    if raw_frames:
        _thumb_save_cache(ck, raw_frames)
    _THUMB_READY.ready.emit(clip_id, raw_frames)
    _extract_sem.release()
    _process_queue()


# ====================================================================
#  片段块 (ClipItem)
# ====================================================================

class ClipItem(QGraphicsRectItem):
    """时间轴上的一个片段块

    支持拖拽移动、拉伸首尾、右键菜单。
    颜色根据类型：视频=蓝 / 音频=绿 / 图片=橙。
    """

    HANDLE_WIDTH = 8         # 拖拽手柄宽度（首尾）
    MIN_VISUAL_WIDTH = 80    # 最小可见宽度（px）— 确保 clip 可见
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

        # 缩略图系统
        self._thumbnails: list[QPixmap] = []   # 已解码的帧缩略图
        self._thumb_loaded = False             # 是否已尝试加载
        self._loading_failed = False           # 加载失败标记
        self._thumb_raw: list[bytes] = []      # 原始 JPEG 字节（从工作线程收到）
        self._thumb_retry = 0
        self._thumb_max_retries = 3

        # 从 thumb_path 加载（如果有）
        tp = self._data.get("thumb_path", "")
        if tp:
            p = QPixmap(tp)
            if not p.isNull():
                self._thumbnails = [p]
                self._thumb_loaded = True

        # 缩略图提取由外部在 addItem 后调用 start_thumb_extraction()
        # 以确保 item 已加入场景，update() 能正确触发重绘

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

    # ---- 缩略图后台提取 ----

    def start_thumb_extraction(self):
        """公开方法：启动后台缩略图提取"""
        self._start_thumb_extraction()

    def _start_thumb_extraction(self):
        """启动后台缩略图提取（加入队列，限制并发）"""
        src = self._data.get("source_path", "")
        if not src or self._thumb_loaded:
            return
        # 文件存在性预检 — 避免无意义入队
        if not Path(src).exists():
            logger.warning(f"[thumb] source file missing: {self.clip_id[:8]} path={src}")
            self._loading_failed = True
            self._thumb_loaded = True
            self.update()
            return
        dur = self._data.get("duration", 0) or 5.0
        ss = self._data.get("source_start", 0)
        se = self._data.get("source_end", dur)

        # 先检查磁盘缓存 — 命中则直接加载，跳过队列和线程
        ck = _thumb_cache_key(src, ss, se)
        cached = _thumb_load_cache(ck)
        if cached:
            logger.info(f"[thumb] cache hit: {self.clip_id[:8]} key={ck[:8]}")
            self._on_thumbs_ready(self.clip_id, cached)
            return

        logger.info(f"[thumb] enqueue: {self.clip_id[:8]} src={Path(src).name} dur={dur:.1f}s")
        _thumb_callbacks[self.clip_id] = self._on_thumbs_ready

        # use queue to limit concurrent ffmpeg processes
        _enqueue_extraction(self.clip_id, src, dur, ss, se)

    def _on_thumbs_ready(self, clip_id: str, raw_frames: list):
        """主线程回调：分帧解码 QPixmap，避免 UI 冻结"""
        if clip_id != self.clip_id or self._thumb_loaded:
            return

        if not raw_frames:
            # retry via queue (with delay to avoid hammering ffmpeg)
            self._thumb_retry += 1
            if self._thumb_retry < self._thumb_max_retries:
                delay = 2000 * self._thumb_retry
                logger.debug(f"[thumb] retry {self._thumb_retry}/{self._thumb_max_retries} in {delay}ms: {self.clip_id[:8]}")
                from PyQt6.QtCore import QTimer
                def retry_later():
                    _thumb_callbacks[self.clip_id] = self._on_thumbs_ready
                    _enqueue_extraction(
                        self.clip_id,
                        self._data.get("source_path", ""),
                        self._data.get("duration", 5.0),
                        self._data.get("source_start", 0),
                        self._data.get("source_end", self._data.get("duration", 5.0)),
                    )
                QTimer.singleShot(delay, retry_later)
            else:
                logger.warning(f"[thumb] all retries exhausted: {self.clip_id[:8]}")
                self._loading_failed = True
                self._thumb_loaded = True
                self.update()
            return

        self._thumb_raw = raw_frames
        self._thumbnails = []
        self._thumb_load_idx = 0
        self._thumb_loaded = True
        self._loading_failed = False

        # staggered QPixmap decoding via QTimer to avoid UI freeze
        from PyQt6.QtCore import QTimer

        def decode_next():
            if self._thumb_load_idx >= len(self._thumb_raw):
                self._thumb_raw = []
                if not self._thumbnails:
                    self._loading_failed = True
                self.update()
                return
            jpeg_bytes = self._thumb_raw[self._thumb_load_idx]
            pix = QPixmap()
            if pix.loadFromData(jpeg_bytes):
                self._thumbnails.append(pix)
            self._thumb_load_idx += 1
            if self._thumb_load_idx < len(self._thumb_raw):
                QTimer.singleShot(5, decode_next)
            else:
                self._thumb_raw = []
                if not self._thumbnails:
                    self._loading_failed = True
                self.update()

        QTimer.singleShot(0, decode_next)

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

        # 多帧缩略图平铺
        thumbs = self._thumbnails
        if thumbs and rect.width() > 40:
            r = rect.adjusted(2, 2, -2, -2)
            painter.save()
            painter.setClipRect(r)
            tw = int(r.width())
            th = int(r.height())
            if th <= 0:
                th = 40
            n = len(thumbs)
            # 每帧至少50px宽，计算实际可容纳帧数
            target_fw = max(50, tw // n)
            actual_n = min(n, max(1, tw // target_fw))
            fw = tw // actual_n
            for i in range(actual_n):
                idx = i * n // actual_n  # uniform sampling
                if idx >= n:
                    idx = n - 1
                pix = thumbs[idx]
                if pix.isNull():
                    continue
                pw, ph = pix.width(), pix.height()
                if pw > 0 and ph > 0:
                    scale = min(fw / pw, th / ph)
                    sw, sh = int(pw * scale), int(ph * scale)
                    ox, oy = (fw - sw) // 2, (th - sh) // 2
                    scaled = pix.scaled(sw, sh,
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                    painter.drawPixmap(int(r.x()) + i * fw + ox, int(r.y()) + oy, scaled)
            painter.restore()
        elif self._loading_failed and rect.width() > 40:
            painter.setPen(QColor(255, 255, 255, 120))
            painter.setFont(QFont("Microsoft YaHei", 16))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎬")
        elif not thumbs and rect.width() > 40:
            painter.setPen(QColor(255, 255, 255, 80))
            painter.setFont(QFont("Microsoft YaHei", 14))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "···")

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
        self._label = QGraphicsTextItem(f"{icons.get(track_type, '📄')} {track_type}", self)
        self._label.setDefaultTextColor(QColor(THEME["text_muted"]))
        self._label.setFont(QFont("Microsoft YaHei", 9))
        self._label.setPos(4, y + TRACK_HEIGHT_DEFAULT / 2 - 10)

    def paint(self, painter: QPainter, option, widget=None):
        """绘制轨道背景 + 虚线网格"""
        super().paint(painter, option, widget)
        rect = self.rect()
        # 虚线网格 — 每秒一条
        painter.setPen(QPen(QColor(THEME["border"]), 1, Qt.PenStyle.DotLine))
        total_sec = rect.width() / PPS
        interval = 1.0 if total_sec <= 30 else (5.0 if total_sec <= 120 else 10.0)
        t = interval
        while t <= total_sec:
            x = t * PPS
            if x > rect.width():
                break
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            t += interval


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
