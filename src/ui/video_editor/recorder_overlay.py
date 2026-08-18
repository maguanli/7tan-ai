"""
视频剪辑器 — 录屏悬浮控制条（Phase 4）

录制时屏幕上显示小型浮动窗口（参见架构文档 8.3）：
    ┌─────────────────────────────┐
    │  🔴 录制中  |  00:12:35   |  ⏸ 暂停  |  ⏹ 停止  |
    └─────────────────────────────┘
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QMouseEvent


class RecorderOverlay(QFrame):
    """录屏悬浮控制条

    特性：
    - 半透明背景，不遮挡被录画面
    - 可拖拽到屏幕任意位置
    - 录制完成自动消失
    - 始终置顶
    """

    # 信号
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    overlay_closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._dragging = False
        self._drag_offset = QPoint()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._blink_dot)

        # 初始位置：屏幕右上角
        from PyQt6.QtGui import QScreen
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.move(geom.right() - self.width() - 20, geom.top() + 20)

    def _setup_ui(self):
        self.setFixedSize(520, 50)
        self.setStyleSheet("""
            RecorderOverlay {
                background: rgba(20, 20, 20, 210);
                border: 1px solid rgba(255, 80, 80, 120);
                border-radius: 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(10)

        # 录制指示灯
        self._dot = QLabel("🔴")
        self._dot.setFont(QFont("Segoe UI", 14))
        self._dot.setStyleSheet("background:transparent; border:none;")
        layout.addWidget(self._dot)

        # 状态文字
        self._status_label = QLabel("录制中")
        self._status_label.setFont(QFont("Microsoft YaHei", 11))
        self._status_label.setStyleSheet(
            "color:#ffffff; background:transparent; border:none;"
        )
        layout.addWidget(self._status_label)

        layout.addStretch()

        # 时间显示
        self._time_label = QLabel("00:00:00")
        self._time_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self._time_label.setStyleSheet(
            "color:#ff5555; background:transparent; border:none; padding:0 10px;"
        )
        layout.addWidget(self._time_label)

        layout.addStretch()

        # 暂停/继续按钮
        self._pause_btn = QPushButton("⏸ 暂停")
        self._pause_btn.setFont(QFont("Microsoft YaHei", 10))
        self._pause_btn.setStyleSheet(self._btn_style("#ffaa00"))
        self._pause_btn.clicked.connect(self._on_pause_resume)
        self._pause_btn.setFixedWidth(80)
        layout.addWidget(self._pause_btn)

        # 停止按钮
        stop_btn = QPushButton("⏹ 停止")
        stop_btn.setFont(QFont("Microsoft YaHei", 10))
        stop_btn.setStyleSheet(self._btn_style("#ff4444"))
        stop_btn.clicked.connect(self._on_stop)
        stop_btn.setFixedWidth(80)
        layout.addWidget(stop_btn)

        # 关闭按钮（独立于停止）
        close_btn = QPushButton("✕")
        close_btn.setFont(QFont("Segoe UI", 10))
        close_btn.setStyleSheet(self._btn_style("#666666"))
        close_btn.clicked.connect(self._on_close)
        close_btn.setFixedSize(28, 28)
        layout.addWidget(close_btn)

        self._blink_visible = True

    def _btn_style(self, accent: str) -> str:
        return f"""
            QPushButton {{
                background: rgba(50,50,50,200);
                color: {accent};
                border: 1px solid {accent}55;
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background: {accent}33;
                border-color: {accent};
            }}
        """

    # ==================================================================
    #  公共方法
    # ==================================================================

    def set_time(self, seconds: float):
        """更新时间显示"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        self._time_label.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def set_paused(self, paused: bool):
        """设置暂停状态"""
        if paused:
            self._status_label.setText("已暂停")
            self._pause_btn.setText("▶ 继续")
            self._dot.setText("⏸")
            self._dot.setStyleSheet("background:transparent; border:none; color:#ffaa00;")
        else:
            self._status_label.setText("录制中")
            self._pause_btn.setText("⏸ 暂停")
            self._dot.setText("🔴")
            self._dot.setStyleSheet("background:transparent; border:none;")

    # ==================================================================
    #  事件处理
    # ==================================================================

    def _on_pause_resume(self):
        if self._status_label.text() == "已暂停":
            self.resume_clicked.emit()
            self.set_paused(False)
        else:
            self.pause_clicked.emit()
            self.set_paused(True)

    def _on_stop(self):
        self.stop_clicked.emit()
        self.hide()

    def _on_close(self):
        self.overlay_closed.emit()
        self.hide()

    def _blink_dot(self):
        """录制指示灯闪烁"""
        if self._status_label.text() == "录制中":
            self._blink_visible = not self._blink_visible
            if self._blink_visible:
                self._dot.setText("🔴")
            else:
                self._dot.setText("⚫")

    # ==================================================================
    #  拖拽支持
    # ==================================================================

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()

    # ==================================================================
    #  显示/隐藏
    # ==================================================================

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start(800)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()
