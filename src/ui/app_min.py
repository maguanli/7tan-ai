"""
7Tan — 原生 PyQt6 桌面应用
所有 UI 组件均使用 PyQt6 原生控件，不依赖 Web 前端
"""
import sys
import json
import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QSplitter, QMessageBox, QProgressBar, QGridLayout, QGroupBox,
    QFormLayout, QTabWidget, QTabBar, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QDialog, QDialogButtonBox,
    QPlainTextEdit, QStatusBar, QInputDialog, QCompleter,
    QTimeEdit,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QAction, QPixmap, QPainter,
    QBrush, QLinearGradient, QRadialGradient, QCursor, QFontDatabase,
    QStandardItemModel, QStandardItem, QPolygonF, QPen,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QUrl, QObject,
    QPropertyAnimation, QEasingCurve, QRect, QRectF, QPointF,
    QTime, QDateTime,
)
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtCharts import (
    QChart, QChartView, QLineSeries, QBarSeries, QBarSet,
    QDateTimeAxis, QValueAxis, QPieSeries, QPieSlice, QBarCategoryAxis,
)

import requests
from loguru import logger

from .theme import THEME

DARK_STYLESHEET = f"""
DARK_STYLESHEET = "test"

class MainWindow(QMainWindow):
    def __init__(self, user_info: dict | None = None):
        super().__init__()
        self._user_info = user_info or {}
        self.setWindowTitle("7Tan — AI工具")
        self.resize(1280, 820)
        self.setMinimumSize(960, 600)
        self._apply_window_icon()

        # 中心 widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        self._sidebar = Sidebar(user_info=self._user_info)
        self._sidebar.page_changed.connect(self._switch_page)
        self._sidebar.open_url.connect(self._on_open_url)
        self._sidebar.logout_requested.connect(self._on_logout)
        main_layout.addWidget(self._sidebar)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {THEME['border']};")
        main_layout.addWidget(sep)

        # 内容区域 — QStackedWidget 容纳所有页面
        self._stack = QStackedWidget()

        self._pages = {}
        self._pages["dashboard"] = DashboardPage()
        self._pages["workspace"] = ChatBrowserSplitPage()
        self._pages["resources"] = ResourceTablePage()
        self._pages["tasks"] = TasksPage()
        self._pages["sources"] = SourcesPage()
        self._pages["analytics"] = AnalyticsPage()
        self._pages["settings"] = SettingsPage()

        for page in self._pages.values():
            self._stack.addWidget(page)

        main_layout.addWidget(self._stack, 1)

        # 将侧边栏对话列表连接到 AI 工作台
        self._pages["workspace"].chat.attach_external_sidebar(self._sidebar.session_sidebar)

        # 状态栏
        self._status = QStatusBar()
        self._status.showMessage(f"🟢 就绪  |  {self._user_info.get('username', '未登录')}")
        self.setStatusBar(self._status)

        # 默认显示仪表盘
        self._sidebar.set_active("dashboard")
        self._stack.setCurrentWidget(self._pages["dashboard"])

    def _apply_window_icon(self):
        """设置窗口图标 — 使用 data/logo/logo_v4_256.png（7Tan LOGO）"""
        try:
            base = Path(__file__).resolve().parents[2]
            for name in ("logo_v4_256.png", "logo_v4_512.png", "logo_v4_1024.png"):
                p = base / "data" / "logo" / name
                if p.exists():
                    self.setWindowIcon(QIcon(str(p)))
                    return
        except Exception:
            pass

    def _switch_page(self, key):
        if key in self._pages:
            self._stack.setCurrentWidget(self._pages[key])
            self._status.showMessage(f"📍 {key}")

    def _on_open_url(self, url: str):
        """侧边栏点击链接 → 切换到 AI 工作台并在浏览器打开"""
        self._sidebar.set_active("workspace")
        self._stack.setCurrentWidget(self._pages["workspace"])
        self._status.showMessage(f"🌐 正在打开 {url}...")
        self._pages["workspace"].navigate_to_url(url)

    def _on_logout(self):
        """退出登录 → 关闭主窗口，重新弹出登录框"""
        self.close()
        launch_app()

    def closeEvent(self, event):
        """关闭窗口时清理：停止录屏 + 等待线程结束"""
        import time
        import threading

        # 停止视频剪辑器中的录屏（防止孤儿 ffmpeg 进程）
        try:
            if hasattr(self, 'video_editor') and self.video_editor is not None:
                recorder = getattr(self.video_editor, '_recorder', None)
                if recorder is not None and getattr(recorder, 'is_recording', False):
                    logger.info("正在停止录屏...")
                    recorder.stop()
        except Exception as e:
            logger.warning(f"停止录屏失败: {e}")

        # 等待非 daemon 线程结束
        for t in threading.enumerate():
            if t is threading.main_thread() or t.daemon:
                continue
            try:
                t.join(timeout=2)
            except Exception:
                pass

        # ===== 保存语音设置到数据库（关闭前兜底）=====
        try:
            workspace = self._pages.get("workspace") if hasattr(self, "_pages") else None
            chat = getattr(workspace, "chat", None) if workspace is not None else None
            if chat is not None and hasattr(chat, "_save_voice_gender"):
                chat._save_voice_gender()
        except Exception as e:
            logger.warning(f"[Voice] 主窗口closeEvent保存语音失败: {e}")

        super().closeEvent(event)


# ===== 启动入口 =====
def launch_app():
