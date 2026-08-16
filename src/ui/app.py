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
    QDesktopServices,
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
from .update_dialog import UpdateDialog
DARK_STYLESHEET = f"""

QMainWindow, QWidget {{

    background-color: {THEME['bg_dark']};

    color: {THEME['text_primary']};

    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;

}}

QPushButton {{

    background-color: {THEME['accent']};

    color: #000;

    border: none;

    border-radius: 6px;

    padding: 8px 20px;

    font-size: 13px;

    font-weight: bold;

}}

QPushButton:hover {{

    background-color: #33ddff;

}}

QPushButton:pressed {{

    background-color: {THEME['accent2']};

    color: #fff;

}}

QPushButton[flat="true"] {{

    background: transparent;

    color: {THEME['text_secondary']};

    padding: 10px 16px;

    border-radius: 6px;

    text-align: left;

    font-weight: normal;

}}

QPushButton[flat="true"]:hover {{

    background-color: {THEME['hover']};

    color: {THEME['text_primary']};

}}

QPushButton[flat="true"][active="true"] {{

    background-color: {THEME['accent']};

    color: #000;

    font-weight: bold;

}}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{

    background-color: {THEME['bg_input']};

    color: {THEME['text_primary']};

    border: 1px solid {THEME['border']};

    border-radius: 6px;

    padding: 8px 12px;

    font-size: 13px;

    selection-background-color: {THEME['accent']};

}}

QComboBox::drop-down {{

    border: none;

    width: 24px;

}}

QComboBox QAbstractItemView {{

    background-color: {THEME['bg_input']};

    color: {THEME['text_primary']};

    selection-background-color: {THEME['accent']};

}}

QTableWidget {{

    background-color: {THEME['bg_card']};

    color: {THEME['text_primary']};

    border: 1px solid {THEME['border']};

    border-radius: 8px;

    gridline-color: {THEME['border']};

    font-size: 12px;

}}

QTableWidget::item {{

    padding: 6px 10px;

}}

QTableWidget::item:selected {{

    background-color: {THEME['accent']};

    color: #000;

}}

QHeaderView::section {{

    background-color: {THEME['bg_dark']};

    color: {THEME['text_secondary']};

    padding: 8px 10px;

    border: none;

    border-bottom: 2px solid {THEME['border']};

    font-weight: bold;

    font-size: 12px;

}}

QScrollBar:vertical {{

    background: {THEME['bg_dark']};

    width: 8px;

    border-radius: 4px;

}}

QScrollBar::handle:vertical {{

    background: {THEME['text_muted']};

    border-radius: 4px;

    min-height: 30px;

}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{

    height: 0;

}}

QProgressBar {{

    background-color: {THEME['bg_input']};

    border: none;

    border-radius: 4px;

    height: 6px;

    text-align: center;

}}

QProgressBar::chunk {{

    background-color: {THEME['accent']};

    border-radius: 4px;

}}

QGroupBox {{

    color: {THEME['text_primary']};

    border: 1px solid {THEME['border']};

    border-radius: 8px;

    margin-top: 12px;

    padding-top: 16px;

    font-weight: bold;

}}

QGroupBox::title {{

    subcontrol-origin: margin;

    left: 12px;

    padding: 0 6px;

}}

QStatusBar {{

    background-color: {THEME['bg_sidebar']};

    color: {THEME['text_muted']};

    font-size: 11px;

}}

QSplitter::handle {{

    background-color: {THEME['border']};

    width: 1px;

}}

QToolTip {{

    background-color: {THEME['bg_card']};

    color: {THEME['text_primary']};

    border: 1px solid {THEME['border']};

    border-radius: 6px;

    padding: 6px 10px;

    font-size: 12px;

}}



/* 弹窗按钮白色字体，确保深色背景上可见 */

QMessageBox {{

    background-color: {THEME['bg_card']};

}}

QMessageBox QPushButton {{

    color: #ffffff;

    background-color: {THEME['accent']};

    min-width: 60px;

}}

QMessageBox QPushButton:hover {{

    color: #ffffff;

    background-color: #33ddff;

}}

"""
import math as _math


def create_refresh_icon(size=40):
    """

    用 QPainter 绘制自定义刷新图标

    返回 QIcon，包含渐变圆弧 + 箭头 + 光晕效果

    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx, cy = size / 2, size / 2
    r = size / 2 - 3
    # 外圈光晕
    glow = QRadialGradient(cx, cy, r)
    glow.setColorAt(0, QColor(124, 58, 237, 35))
    glow.setColorAt(0.7, QColor(0, 212, 255, 18))
    glow.setColorAt(1, QColor(124, 58, 237, 0))
    painter.setBrush(QBrush(glow))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
    # 渐变圆弧 — 用分段绘制模拟渐变
    pen = QPen()
    pen.setWidthF(max(3.0, size / 14))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    arc_r = r * 0.70
    rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
    segments = [
        (270, 90, QColor(124, 58, 237)),     # 紫 (270°→360°)
        (0, 90, QColor(0, 212, 255)),         # 青 (0°→90°)
        (180, 90, QColor(100, 150, 255, 160)),  # 淡蓝 (180°→270°)
    ]
    for start_angle, span, color in segments:
        pen.setColor(color)
        painter.setPen(pen)
        painter.drawArc(rect, start_angle * 16, span * 16)
    # 箭头（在 350° 位置）
    arrow_angle = 348
    rad = _math.radians(arrow_angle)
    tip_x = cx + arc_r * _math.cos(rad)
    tip_y = cy + arc_r * _math.sin(rad)
    arrow_sz = max(5, size / 7)
    tangent_rad = _math.radians(arrow_angle - 90)
    arrow = QPolygonF()
    arrow.append(QPointF(tip_x, tip_y))
    arrow.append(QPointF(
        tip_x + arrow_sz * _math.cos(tangent_rad) - arrow_sz * 0.55 * _math.cos(rad),
        tip_y + arrow_sz * _math.sin(tangent_rad) - arrow_sz * 0.55 * _math.sin(rad),
    ))
    arrow.append(QPointF(
        tip_x - arrow_sz * _math.cos(tangent_rad) - arrow_sz * 0.55 * _math.cos(rad),
        tip_y - arrow_sz * _math.sin(tangent_rad) - arrow_sz * 0.55 * _math.sin(rad),
    ))
    painter.setBrush(QBrush(QColor(0, 212, 255)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(arrow)
    # 中心光点
    painter.setBrush(QBrush(QColor(124, 58, 237, 80)))
    painter.drawEllipse(QPointF(cx, cy), 2.5, 2.5)
    painter.end()
    return QIcon(pixmap)
# ===== API 基础 URL =====
import os as _os
_API_PORT = _os.environ.get("7TAN_PORT", "9800")
API_BASE = f"http://127.0.0.1:{_API_PORT}"
# ===== 后台请求线程 =====
# ============================================================
#  API Worker - 后台线程
# ============================================================

class ApiWorker(QThread):
    """后台 HTTP 请求线程，避免阻塞 UI"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)


    def __init__(self, method, url, data=None):
        super().__init__()
        self._method = method
        self._url = url
        self._data = data


    def run(self):
        try:
            if self._method == "GET":
                resp = requests.get(self._url, timeout=30)
            elif self._method == "POST":
                resp = requests.post(self._url, json=self._data, timeout=1800)
            elif self._method == "PUT":
                resp = requests.put(self._url, json=self._data, timeout=30)
            elif self._method == "DELETE":
                resp = requests.delete(self._url, timeout=30)
            else:
                self.error.emit(f"未知方法: {self._method}")
                return
            resp.raise_for_status()
            self.finished.emit(resp.json() if resp.text else {"ok": True})
        except Exception as e:
            self.error.emit(str(e))
# ===== 统计卡片组件 =====
# ============================================================
#  StatCard - 统计卡片组件
# ============================================================

class StatCard(QFrame):

    def __init__(self, title, value="0", subtitle="", color=THEME["accent"]):
        super().__init__()
        self.setStyleSheet(f"""

            QFrame {{

                background-color: {THEME['bg_card']};

                border: 1px solid {THEME['border']};

                border-radius: 10px;

                padding: 16px;

            }}

        """)
        self.setMinimumHeight(100)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 12px;")
        self._value_label = QLabel(str(value))
        self._value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        self._sub_label = QLabel(subtitle)
        self._sub_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)
        layout.addWidget(self._sub_label)


    def set_value(self, value, subtitle=""):
        self._value_label.setText(str(value))
        if subtitle:
            self._sub_label.setText(subtitle)
# ===== 侧边栏 =====
# ============================================================
#  Sidebar - 侧边栏导航
# ============================================================


class Sidebar(QFrame):
    page_changed = pyqtSignal(str)
    open_url = pyqtSignal(str)
    logout_requested = pyqtSignal()


    def __init__(self, user_info: dict | None = None):
        super().__init__()
        self.setObjectName("sidebar_frame")
        self.setFixedWidth(220)
        self.setStyleSheet(f"background-color: {THEME['bg_sidebar']};")
        self._buttons = {}
        self._active_key = ""
        self._user_info = user_info or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)
        # Logo: AI 机器人图标 + 7Tan 文字（图标缺失时回退 emoji）
        logo_row = QWidget()
        logo_row.setObjectName("sidebar_logo_row")
        logo_layout = QHBoxLayout(logo_row)
        logo_layout.setContentsMargins(8, 8, 8, 8)
        logo_layout.setSpacing(8)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(25, 25)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if getattr(sys, "_MEIPASS", None):
            _icon_path = Path(sys._MEIPASS) / "data" / "logo" / "sidebar_icon.png"
        else:
            _icon_path = Path(__file__).resolve().parent.parent.parent / "data" / "logo" / "sidebar_icon.png"
        _icon_pix = QPixmap(str(_icon_path)) if _icon_path.exists() else QPixmap()
        if not _icon_pix.isNull():
            icon_lbl.setPixmap(_icon_pix.scaled(
                25, 25,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        else:
            icon_lbl.setText("🤖")
        text_lbl = QLabel("7Tan")
        text_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        text_lbl.setStyleSheet(
            f"color: {THEME['accent']}; font-size: 16px; font-weight: bold; background: transparent;"
        )
        logo_layout.addWidget(icon_lbl)
        logo_layout.addWidget(text_lbl)
        layout.addWidget(logo_row)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {THEME['border']};")
        layout.addWidget(line)
        layout.addSpacing(8)
        # 可滚动的上部区域（导航按钮 + 对话列表）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""

            QScrollArea {{

                background: transparent;

                border: none;

            }}

            QScrollBar:vertical {{

                background: {THEME['bg_dark']};

                width: 6px;

                border-radius: 3px;

            }}

            QScrollBar::handle:vertical {{

                background: {THEME['text_muted']};

                border-radius: 3px;

                min-height: 20px;

            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{

                height: 0;

            }}

        """)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)
        # 导航项
        nav_items = [
            ("workspace", "💬", "AI 工作台"),
            ("market", "🛒", "插件市场"),
            ("resources", "📦", "资源管理"),
            ("tasks", "⚙️", "任务监控"),
            ("sources", "🔗", "数据源"),
            ("analytics", "📈", "统计分析"),
            ("settings", "🔧", "设置"),
        ]
        for key, icon, label in nav_items:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""

                QPushButton {{

                    background: transparent;

                    color: {THEME['text_secondary']};

                    padding: 10px 16px;

                    border-radius: 6px;

                    text-align: left;

                    font-weight: normal;

                    border: none;

                }}

                QPushButton:hover {{

                    background-color: {THEME['hover']};

                    color: {THEME['text_primary']};

                }}

            """)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            self._buttons[key] = btn
            scroll_layout.addWidget(btn)
        # 对话列表 — 放在设置下方，仅 AI 工作台时可见
        self._session_sidebar = SessionSidebar()
        self._session_sidebar.setFixedWidth(184)
        self._session_sidebar.hide()
        scroll_layout.addWidget(self._session_sidebar)
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)
        # 不再需要单独的 stretch，scroll_area 的 stretch factor 1 已处理
        # --- 帮助链接：问题求助 | 投诉建议（并排，用户信息上方） ---
        links_row = QWidget()
        links_row.setObjectName("sidebar_links")
        links_layout = QHBoxLayout(links_row)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(4)


        def _make_side_link(text, url):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {THEME['text_secondary']}; font-size: 12px; "
                f"padding: 6px 4px; border-radius: 4px;"
            )
            lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setToolTip(f"在浏览器中打开 {url}")
            lbl.mousePressEvent = lambda e, u=url: self.open_url.emit(u)
            return lbl
        # --- 顶部链接：7坛社区 | 现金任务（并排，问题求助上方） ---
        links_row_top = QWidget()
        links_row_top.setObjectName("sidebar_links")
        links_layout_top = QHBoxLayout(links_row_top)
        links_layout_top.setContentsMargins(0, 0, 0, 0)
        links_layout_top.setSpacing(4)
        links_layout_top.addWidget(_make_side_link("🌐 7坛社区", "https://www.7tan.com/bbs/"), 1)
        links_layout_top.addWidget(_make_side_link("💰 现金任务", "https://www.7tan.com/bbs/board/3/"), 1)
        layout.addWidget(links_row_top)
        layout.addSpacing(4)
        links_layout.addWidget(_make_side_link("🙋 问题求助", "https://www.7tan.com/bbs/board/25/"), 1)
        links_layout.addWidget(_make_side_link("📮 投诉建议", "https://www.7tan.com/bbs/board/26/"), 1)
        layout.addWidget(links_row)
        layout.addSpacing(4)
        # --- 完整版状态组件 ---
        from .pro_status_widget import ProStatusWidget
        self._pro_widget = ProStatusWidget(user_info=self._user_info)
        self._pro_widget.logout_requested.connect(self.logout_requested.emit)
        layout.addWidget(self._pro_widget)
        layout.addSpacing(8)
        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"color: {THEME['border']};")
        layout.addWidget(line2)
        # 底部信息
        try:
            from src.config.version import APP_VERSION as _APP_VERSION
        except Exception:
            _APP_VERSION = "1.0.0"
        version = QLabel(f"7tan.com v{_APP_VERSION}")
        version.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 14px; font-weight: bold; padding: 10px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        from src.config.loader import load_config as _load_cfg4
        _cfg4 = _load_cfg4()
        _base4 = _cfg4.get("site_7tan", {}).get("base_url", "")
        _site_root4 = _base4.replace("/api", "") if _base4 else "https://www.7tan.com"
        _site_root4 = _site_root4.replace("img.7tan.cn", "www.7tan.com")
        version.setToolTip(f"在浏览器中打开 {_site_root4}")
        version.mousePressEvent = lambda e: self.open_url.emit(_site_root4 + "/")
        layout.addWidget(version)
        # 底部版权信息
        copyright_label = QLabel("© 7坛版权所有")
        copyright_label.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 11px; padding: 0 10px 6px 10px;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)


    def _on_click(self, key):
        if key == "market":
            # 插件市场 → 打开软件内嵌插件市场（设置页）
            self.set_active(key)
            self._session_sidebar.setVisible(False)
            self.page_changed.emit(key)
            return
        self.set_active(key)
        # 仅在 AI 工作台时显示对话列表
        self._session_sidebar.setVisible(key == "workspace")
        self.page_changed.emit(key)
    @property

    def session_sidebar(self):
        return self._session_sidebar


    def set_active(self, key):
        btn_active_style = f"""

            QPushButton {{

                background-color: {THEME['accent']};

                color: #000;

                font-weight: bold;

                padding: 10px 16px;

                border-radius: 6px;

                text-align: left;

                border: none;

            }}

        """
        btn_inactive_style = f"""

            QPushButton {{

                background: transparent;

                color: {THEME['text_secondary']};

                padding: 10px 16px;

                border-radius: 6px;

                text-align: left;

                font-weight: normal;

                border: none;

            }}

            QPushButton:hover {{

                background-color: {THEME['hover']};

                color: {THEME['text_primary']};

            }}

        """
        for k, btn in self._buttons.items():
            if k == key:
                btn.setStyleSheet(btn_active_style)
            else:
                btn.setStyleSheet(btn_inactive_style)
        self._active_key = key
# ===== 仪表盘页面 =====
# ============================================================
#  DashboardPage - 仪表盘
# ============================================================

class DashboardPage(QWidget):

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        # 标题
        title = QLabel("📊 仪表盘")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)
        # 统计卡片网格
        self._cards_layout = QGridLayout()
        self._cards_layout.setSpacing(12)
        self._card_published = StatCard("已发布资源", "—", "全部完成发布的游戏/软件", THEME["success"])
        self._card_progress = StatCard("处理中", "—", "正在下载/改写/上传", THEME["warning"])
        self._card_month = StatCard("本月新增", "—", "当月采集资源", THEME["accent"])
        self._card_cost = StatCard("今日费用", "—", "API调用费用", THEME["accent2"])
        self._cards_layout.addWidget(self._card_published, 0, 0)
        self._cards_layout.addWidget(self._card_progress, 0, 1)
        self._cards_layout.addWidget(self._card_month, 1, 0)
        self._cards_layout.addWidget(self._card_cost, 1, 1)
        layout.addLayout(self._cards_layout)
        # 系统状态
        status_group = QGroupBox("系统状态")
        status_layout = QFormLayout(status_group)
        self._lbl_success = QLabel("—")
        self._lbl_cpu = QLabel("—")
        self._lbl_mem = QLabel("—")
        self._lbl_ws = QLabel("—")
        self._lbl_uptime = QLabel("—")
        for label, widget in [
            ("成功率:", self._lbl_success),
            ("CPU:", self._lbl_cpu),
            ("内存:", self._lbl_mem),
            ("连接数:", self._lbl_ws),
            ("运行时间:", self._lbl_uptime),
        ]:
            label_w = QLabel(label)
            label_w.setStyleSheet(f"color: {THEME['text_secondary']};")
            status_layout.addRow(label_w, widget)
        layout.addWidget(status_group)
        layout.addStretch()
        # 定时刷新（仅页面可见时生效）
        self._timer = QTimer()
        self._timer.timeout.connect(self.refresh)


    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start(10000)
        self.refresh()


    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()


    def refresh(self):
        self._worker = ApiWorker("GET", f"{API_BASE}/api/stats/dashboard")
        self._worker.finished.connect(self._on_data)
        self._worker.error.connect(lambda e: logger.error(f"仪表盘加载失败: {e}"))
        self._worker.start()


    def _on_data(self, data):
        self._card_published.set_value(
            data.get("total_published", 0),
            f"成功率 {data.get('success_rate', 100)}%"
        )
        self._card_progress.set_value(data.get("in_progress", 0), "进行中任务")
        self._card_month.set_value(data.get("this_month_new", 0), "本月新增资源")
        self._card_cost.set_value(f"¥{data.get('today_cost', 0):.4f}", "今日 API 费用")
        sys_info = data.get("system", {})
        if isinstance(sys_info, str):
            sys_info = {}
        self._lbl_success.setText(f"{data.get('success_rate', 100)}%")
        self._lbl_cpu.setText(f"{sys_info.get('cpu_percent', 0)}%")
        self._lbl_mem.setText(f"{sys_info.get('memory_percent', 0)}%")
        self._lbl_ws.setText(str(sys_info.get('ws_connections', 0)))
        self._lbl_uptime.setText(str(sys_info.get('uptime', '—')))
# ===== 导入重写的 ChatPage（from chat_page.py）=====
from .chat_page import ChatPage, MessageInput, SessionSidebar
# ===== 资源管理页面（表格） =====
# ============================================================
#  ResourceTablePage - 资源列表
# ============================================================

class ResourceTablePage(QWidget):

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("📦 资源管理")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)
        # 筛选工具栏
        filter_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索资源名称...")
        self._search_input.setFixedWidth(250)
        filter_layout.addWidget(self._search_input)
        self._type_combo = QComboBox()
        self._type_combo.addItems(["全部类型", "game", "software", "other"])
        self._type_combo.setFixedWidth(120)
        filter_layout.addWidget(self._type_combo)
        self._status_combo = QComboBox()
        self._status_combo.addItems(["全部状态", "published", "pending", "downloading", "rewriting", "failed"])
        self._status_combo.setFixedWidth(120)
        filter_layout.addWidget(self._status_combo)
        search_btn = QPushButton("🔍 搜索")
        search_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(search_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["ID", "标题", "类型", "来源", "状态", "创建时间"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""

            QTableWidget {{ alternate-background-color: {THEME['bg_input']}; }}

        """)
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table, 1)
        # 底部工具栏
        bottom = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh)
        bottom.addWidget(refresh_btn)
        delete_btn = QPushButton("🗑️ 删除选中")
        delete_btn.setStyleSheet(f"""

            QPushButton {{

                background-color: {THEME['danger']};

                color: #fff;

                border: none;

                border-radius: 6px;

                padding: 8px 16px;

                font-size: 13px;

                font-weight: bold;

            }}

            QPushButton:hover {{

                background-color: #ff4444;

            }}

        """)
        delete_btn.clicked.connect(self._delete_selected)
        bottom.addWidget(delete_btn)
        bottom.addStretch()
        self._count_label = QLabel("共 0 条")
        self._count_label.setStyleSheet(f"color: {THEME['text_muted']};")
        bottom.addWidget(self._count_label)
        layout.addLayout(bottom)
        self._timer = QTimer()
        self._timer.timeout.connect(self.refresh)


    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start(30000)
        self.refresh()


    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()


    def refresh(self):
        params = {}
        search = self._search_input.text().strip()
        if search:
            params["search"] = search
        rt = self._type_combo.currentText()
        if rt != "全部类型":
            params["resource_type"] = rt
        st = self._status_combo.currentText()
        if st != "全部状态":
            params["status"] = st
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{API_BASE}/api/resources?{qs}" if qs else f"{API_BASE}/api/resources"
        self._worker = ApiWorker("GET", url)
        self._worker.finished.connect(self._on_data)
        self._worker.error.connect(lambda e: logger.error(f"资源加载失败: {e}"))
        self._worker.start()


    def _on_data(self, data):
        resources = data.get("resources", [])
        total = data.get("total", 0)
        self._count_label.setText(f"共 {total} 条")
        self._table.setRowCount(len(resources))
        for i, r in enumerate(resources):
            self._table.setItem(i, 0, QTableWidgetItem(str(r.get("id", ""))))
            self._table.setItem(i, 1, QTableWidgetItem(r.get("title", "")))
            self._table.setItem(i, 2, QTableWidgetItem(r.get("resource_type", "")))
            status = r.get("status", "")
            status_item = QTableWidgetItem(status)
            color = {"published": THEME["success"], "failed": THEME["danger"],
                     "pending": THEME["warning"]}.get(status, THEME["text_secondary"])
            status_item.setForeground(QColor(color))
            self._table.setItem(i, 4, status_item)
            self._table.setItem(i, 3, QTableWidgetItem(r.get("source_site", "")))
            self._table.setItem(i, 5, QTableWidgetItem(
                r.get("created_at", "")[:19] if r.get("created_at") else ""
            ))


    def _on_double_click(self, index):
        row = index.row()
        rid = self._table.item(row, 0).text()
        title = self._table.item(row, 1).text()
        QMessageBox.information(self, "资源详情", f"ID: {rid}\n标题: {title}\n\n完整详情功能开发中...")


    def _on_context_menu(self, pos):
        """右键菜单"""
        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ 删除")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == delete_action:
            self._delete_selected()


    def _delete_selected(self):
        """删除选中的资源"""
        selected = self._table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选中要删除的资源")
            return
        ids = []
        titles = []
        for idx in selected:
            row = idx.row()
            rid = self._table.item(row, 0).text()
            title = self._table.item(row, 1).text()
            ids.append(rid)
            titles.append(title)
        names = "\n".join(f"  [{i}] {t}" for i, t in zip(ids, titles))
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除以下 {len(ids)} 个资源吗？\n\n{names}\n\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        deleted = 0
        failed = 0
        for rid in ids:
            try:
                resp = requests.delete(f"{API_BASE}/api/resources/{rid}", timeout=10)
                if resp.status_code == 200:
                    deleted += 1
                else:
                    failed += 1
                    logger.error(f"删除失败 ID={rid}: {resp.text}")
            except Exception as e:
                failed += 1
                logger.error(f"删除异常 ID={rid}: {e}")
        if failed == 0:
            QMessageBox.information(self, "完成", f"已删除 {deleted} 个资源")
        else:
            QMessageBox.warning(self, "完成", f"成功 {deleted} 个，失败 {failed} 个")
        self.refresh()
# ===== 任务监控页面 =====
# ============================================================
#  TasksPage - 任务管理 + 定时采集
# ============================================================

class TasksPage(QWidget):

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("⚙️ 任务监控")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)
        # ===== 定时采集设置 =====
        sched_group = QGroupBox("⏰ 定时采集")
        sched_group.setStyleSheet(f"""

            QGroupBox {{

                font-size: 15px; font-weight: bold; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 8px;

                margin-top: 12px; padding: 20px 16px 16px 16px;

            }}

            QGroupBox::title {{ subcontrol-origin: margin; left: 16px; padding: 0 8px; }}

        """)
        sched_layout = QVBoxLayout(sched_group)
        sched_layout.setSpacing(10)
        # 开关行
        toggle_row = QHBoxLayout()
        toggle_label = QLabel("定时采集:")
        toggle_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 13px; font-weight: normal;")
        self._sched_enable_btn = QPushButton("▶ 启用采集")
        self._sched_enable_btn.setFixedWidth(140)
        self._sched_enable_btn.clicked.connect(lambda: self._toggle_scheduler(True))
        self._sched_enable_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['success']}; color: #fff; border: none;

                border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: bold;

            }}

            QPushButton:hover {{ background: #059669; }}

        """)
        self._sched_disable_btn = QPushButton("⏸ 关闭采集")
        self._sched_disable_btn.setFixedWidth(140)
        self._sched_disable_btn.clicked.connect(lambda: self._toggle_scheduler(False))
        self._sched_disable_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['danger']}; color: #fff; border: none;

                border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: bold;

            }}

            QPushButton:hover {{ background: #dc2626; }}

        """)
        self._sched_status = QLabel("")
        self._sched_status.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 13px;")
        toggle_row.addWidget(toggle_label)
        toggle_row.addWidget(self._sched_enable_btn)
        toggle_row.addWidget(self._sched_disable_btn)
        toggle_row.addWidget(self._sched_status)
        toggle_row.addStretch()
        sched_layout.addLayout(toggle_row)
        # 三个时间选择器
        times_layout = QHBoxLayout()
        times_layout.setSpacing(16)
        self._time_pickers = {}
        for label, name, default_h in [
            ("🌅 早间", "每日早间更新", "08"),
            ("☀️ 午间", "每日午间更新", "12"),
            ("🌙 晚间", "每日晚间更新", "18"),
        ]:
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px; font-weight: normal;")
            col.addWidget(lbl)
            time_edit = QTimeEdit(QTime(int(default_h), 0))
            time_edit.setDisplayFormat("HH:mm")
            time_edit.setStyleSheet(f"""

                QTimeEdit {{

                    background: {THEME['bg_dark']}; color: {THEME['text_primary']};

                    border: 1px solid {THEME['border']}; border-radius: 6px;

                    padding: 8px 12px; font-size: 15px; font-weight: bold;

                }}

                QTimeEdit:hover {{ border-color: {THEME['accent']}; }}

            """)
            col.addWidget(time_edit)
            self._time_pickers[name] = time_edit
            times_layout.addLayout(col)
        sched_layout.addLayout(times_layout)
        # 按钮行
        btn_row = QHBoxLayout()
        self._sched_save_btn = QPushButton("💾 保存设置")
        self._sched_save_btn.clicked.connect(self._save_scheduler_config)
        self._sched_save_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['accent']}; color: #000; border: none;

                border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: bold;

            }}

            QPushButton:hover {{ background: #33ddff; }}

        """)
        self._sched_next_label = QLabel("")
        self._sched_next_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        btn_row.addWidget(self._sched_save_btn)
        btn_row.addWidget(self._sched_next_label)
        btn_row.addStretch()
        sched_layout.addLayout(btn_row)
        layout.addWidget(sched_group)
        # 统计
        stats_layout = QHBoxLayout()
        self._card_active = StatCard("活跃任务", "0", "正在执行", THEME["warning"])
        self._card_queued = StatCard("排队中", "0", "等待执行", THEME["accent"])
        stats_layout.addWidget(self._card_active)
        stats_layout.addWidget(self._card_queued)
        layout.addLayout(stats_layout)
        # 任务列表
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["任务ID", "类型", "状态", "进度", "开始时间"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, 1)
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)
        self._timer = QTimer()
        self._timer.timeout.connect(self.refresh)


    def _toggle_scheduler(self, enable: bool):
        times = {name: picker.time().toString("HH:mm") for name, picker in self._time_pickers.items()}
        payload = {"enabled": enable, "times": times}
        self._edit_worker = ApiWorker("PUT", f"{API_BASE}/api/settings/scheduler", payload)
        self._edit_worker.finished.connect(lambda d: self._on_scheduler_saved(enable))
        self._edit_worker.error.connect(lambda e: QMessageBox.warning(self, "错误", f"操作失败: {e}"))
        self._edit_worker.start()
        self._keep_worker(self._edit_worker)


    def _on_scheduler_saved(self, enabled: bool):
        if enabled:
            self._sched_status.setText("✅ 采集已启用")
            self._sched_status.setStyleSheet(f"color: {THEME['success']}; font-size: 13px; font-weight: bold;")
        else:
            self._sched_status.setText("⏸ 采集已停止")
            self._sched_status.setStyleSheet(f"color: {THEME['danger']}; font-size: 13px; font-weight: bold;")
        self._load_scheduler_config()


    def _save_scheduler_config(self):
        self._toggle_scheduler(True)


    def _load_scheduler_config(self):
        worker = ApiWorker("GET", f"{API_BASE}/api/settings/scheduler")
        worker.finished.connect(self._on_scheduler_data)
        worker.error.connect(lambda e: logger.warning(f"加载调度配置失败: {e}"))
        worker.start()
        self._keep_worker(worker)


    def _on_scheduler_data(self, data):
        enabled = data.get("enabled", True)
        if enabled:
            self._sched_status.setText("✅ 采集已启用")
            self._sched_status.setStyleSheet(f"color: {THEME['success']}; font-size: 13px; font-weight: bold;")
        else:
            self._sched_status.setText("⏸ 采集已停止")
            self._sched_status.setStyleSheet(f"color: {THEME['danger']}; font-size: 13px; font-weight: bold;")
        # 加载时间
        times = data.get("times", {})
        for name, picker in self._time_pickers.items():
            time_str = times.get(name, "")
            if time_str:
                h, m = time_str.split(":") if ":" in time_str else (time_str, "0")
                picker.setTime(QTime(int(h), int(m)))
        # 显示下次运行时间
        next_jobs = data.get("next_jobs", [])
        if next_jobs:
            lines = ["下次采集:"]
            for job in next_jobs[:3]:
                t = job.get("next_run", "")
                if t:
                    dt = t.replace("T", " ")[:16]
                    lines.append(f"  {job['name'][:4]} {dt}")
            self._sched_next_label.setText("\n".join(lines))
        else:
            self._sched_next_label.setText("调度器未运行")


    def _keep_worker(self, worker):
        """保持 worker 引用防止 GC"""
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.finished.connect(lambda d, w=worker: self._workers.remove(w) if w in self._workers else None)
        worker.error.connect(lambda e, w=worker: self._workers.remove(w) if w in self._workers else None)


    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start(5000)
        self.refresh()
        self._load_scheduler_config()


    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()


    def refresh(self):
        self._worker = ApiWorker("GET", f"{API_BASE}/api/tasks")
        self._worker.finished.connect(self._on_data)
        self._worker.error.connect(lambda e: logger.error(f"任务加载失败: {e}"))
        self._worker.start()
        self._keep_worker(self._worker)


    def _on_data(self, data):
        stats = data.get("stats", {})
        self._card_active.set_value(str(stats.get("active_count", 0)))
        self._card_queued.set_value(str(stats.get("queued_count", 0)))
        active = data.get("active", [])
        queued = data.get("queued", [])
        all_tasks = active + queued
        self._table.setRowCount(len(all_tasks))
        for i, t in enumerate(all_tasks):
            self._table.setItem(i, 0, QTableWidgetItem(t.get("id", "")))
            self._table.setItem(i, 1, QTableWidgetItem(t.get("type", "")))
            self._table.setItem(i, 2, QTableWidgetItem(t.get("status", "")))
            progress = t.get("progress", 0)
            if isinstance(progress, (int, float)):
                bar = QProgressBar()
                bar.setValue(int(progress))
                self._table.setCellWidget(i, 3, bar)
            else:
                self._table.setItem(i, 3, QTableWidgetItem(str(progress)))
            self._table.setItem(i, 4, QTableWidgetItem(str(t.get("started_at", ""))))


    def _on_context_menu(self, pos):
        """右键菜单 — 删除任务"""
        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ 删除")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == delete_action:
            self._delete_selected_task()


    def _delete_selected_task(self):
        selected = self._table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选中要删除的任务")
            return
        ids = []
        for idx in selected:
            row = idx.row()
            tid = self._table.item(row, 0).text()
            if tid:
                ids.append(tid)
        if not ids:
            return
        for tid in ids:
            try:
                self._worker = ApiWorker("DELETE", f"{API_BASE}/api/scheduler/job/{tid}")
                self._worker.finished.connect(self.refresh)
                self._worker.start()
            except Exception as e:
                logger.error(f"删除任务失败: {e}")
# ===== 数据源管理页面 =====
# ============================================================
#  SourcesPage - 源站管理
# ============================================================

class SourcesPage(QWidget):

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("🌐 数据源管理")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)
        # 按钮行
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 添加源站")
        add_btn.clicked.connect(self._add_source)
        add_btn.setFixedWidth(120)
        btn_row.addWidget(add_btn)
        self._edit_btn = QPushButton("✏️ 编辑选中")
        self._edit_btn.clicked.connect(self._edit_selected)
        self._edit_btn.setFixedWidth(120)
        btn_row.addWidget(self._edit_btn)
        self._del_btn = QPushButton("🗑 删除选中")
        self._del_btn.clicked.connect(self._delete_selected)
        self._del_btn.setFixedWidth(120)
        self._del_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['danger']}; color: #fff; border: none;

                border-radius: 6px; padding: 8px 16px; font-size: 13px;

            }}

            QPushButton:hover {{ background: #dc2626; }}

        """)
        btn_row.addWidget(self._del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["ID", "名称", "URL", "类型", "需登录", "状态", "上次爬取"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnHidden(0, True)  # 隐藏 ID 列
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self._table, 1)
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)


    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()


    def refresh(self):
        self._worker = ApiWorker("GET", f"{API_BASE}/api/sources")
        self._worker.finished.connect(self._on_data)
        self._worker.error.connect(lambda e: logger.error(f"数据源加载失败: {e}"))
        self._worker.start()


    def _on_data(self, data):
        sources = data.get("sources", [])
        self._table.setRowCount(len(sources))
        for i, s in enumerate(sources):
            self._table.setItem(i, 0, QTableWidgetItem(str(s.get("id", ""))))
            self._table.setItem(i, 1, QTableWidgetItem(s.get("name", "")))
            self._table.setItem(i, 2, QTableWidgetItem(s.get("url", "")))
            self._table.setItem(i, 3, QTableWidgetItem(s.get("site_type", "")))
            self._table.setItem(i, 4, QTableWidgetItem("是" if s.get("need_login") else "否"))
            enabled = s.get("enabled", True)
            status_item = QTableWidgetItem("启用" if enabled else "禁用")
            status_item.setForeground(QColor(THEME["success"] if enabled else THEME["danger"]))
            self._table.setItem(i, 5, status_item)
            self._table.setItem(i, 6, QTableWidgetItem(str(s.get("last_crawl_at", "—"))))


    def _get_selected_source(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先在表格中选择一个源站")
            return None
        return {
            "id": self._table.item(row, 0).text(),
            "name": self._table.item(row, 1).text(),
            "url": self._table.item(row, 2).text(),
            "site_type": self._table.item(row, 3).text(),
            "need_login": self._table.item(row, 4).text() == "是",
            "enabled": self._table.item(row, 5).text() == "启用",
        }


    def _edit_selected(self):
        source = self._get_selected_source()
        if not source:
            return
        self._open_edit_dialog(source)


    def _open_edit_dialog(self, source: dict):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑源站 - {source['name']}")
        dialog.setMinimumWidth(450)
        dialog_layout = QFormLayout(dialog)
        name_edit = QLineEdit(source.get("name", ""))
        url_edit = QLineEdit(source.get("url", ""))
        type_combo = QComboBox()
        type_combo.addItems(["game", "software", "both", "other"])
        type_combo.setCurrentText(source.get("site_type", "game"))
        need_login = QCheckBox()
        need_login.setChecked(source.get("need_login", False))
        enabled_check = QCheckBox()
        enabled_check.setChecked(source.get("enabled", True))
        dialog_layout.addRow("名称:", name_edit)
        dialog_layout.addRow("URL:", url_edit)
        dialog_layout.addRow("类型:", type_combo)
        dialog_layout.addRow("需要登录:", need_login)
        dialog_layout.addRow("启用:", enabled_check)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._edit_worker = ApiWorker("PUT", f"{API_BASE}/api/sources/{source['id']}", {
                "name": name_edit.text(),
                "url": url_edit.text(),
                "site_type": type_combo.currentText(),
                "need_login": need_login.isChecked(),
                "enabled": enabled_check.isChecked(),
            })
            self._edit_worker.finished.connect(lambda d: self.refresh())
            self._edit_worker.error.connect(lambda e: QMessageBox.warning(self, "错误", f"编辑失败: {e}"))
            self._edit_worker.start()


    def _delete_selected(self):
        source = self._get_selected_source()
        if not source:
            return
        reply = QMessageBox.question(self, "确认删除",
            f"确定要删除源站 '{source['name']}' 吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._del_worker = ApiWorker("DELETE", f"{API_BASE}/api/sources/{source['id']}")
            self._del_worker.finished.connect(lambda d: self.refresh())
            self._del_worker.error.connect(lambda e: QMessageBox.warning(self, "错误", f"删除失败: {e}"))
            self._del_worker.start()


    def _add_source(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加源站")
        dialog.setMinimumWidth(400)
        dialog_layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        url_edit = QLineEdit()
        type_combo = QComboBox()
        type_combo.addItems(["game", "software", "both", "other"])
        need_login = QCheckBox()
        dialog_layout.addRow("名称:", name_edit)
        dialog_layout.addRow("URL:", url_edit)
        dialog_layout.addRow("类型:", type_combo)
        dialog_layout.addRow("需要登录:", need_login)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._worker2 = ApiWorker("POST", f"{API_BASE}/api/sources", {
                "name": name_edit.text(),
                "url": url_edit.text(),
                "site_type": type_combo.currentText(),
                "need_login": need_login.isChecked(),
                "crawl_interval": 360,
            })
            self._worker2.finished.connect(lambda d: self.refresh())
            self._worker2.error.connect(lambda e: QMessageBox.warning(self, "错误", f"添加失败: {e}"))
            self._worker2.start()


    def _on_context_menu(self, pos):
        """右键菜单 — 删除源站"""
        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ 删除")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == delete_action:
            self._delete_selected_source()


    def _delete_selected_source(self):
        selected = self._table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选中要删除的源站")
            return
        for idx in selected:
            row = idx.row()
            sid = self._table.item(row, 0).text()
            if sid:
                try:
                    self._worker3 = ApiWorker("DELETE", f"{API_BASE}/api/sources/{sid}")
                    self._worker3.finished.connect(self.refresh)
                    self._worker3.start()
                except Exception as e:
                    logger.error(f"删除源站失败: {e}")
# ===== 独立浏览器窗口 =====
# ============================================================
#  DetachedBrowserWindow - 独立浏览器窗口
# ============================================================

class DetachedBrowserWindow(QMainWindow):
    """弹出式独立浏览器窗口"""


    def __init__(self, url: str = "about:blank", title: str = "独立窗口", view=None):
        super().__init__()
        self.setWindowTitle(f"🌐 {title}")
        self.resize(1024, 700)
        self.setMinimumSize(400, 300)
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        if view is not None:
            self._view = view
            # view 已有页面内容，仅连接信号，不重新加载
        else:
            self._view = QWebEngineView()
            import src.tools.browser_tools as bt
            bt.register_web_view(self._view)
            if url and url != "about:blank":
                self._view.load(QUrl(url))
            else:
                self._view.setHtml("<h2 style='color:#aaa;text-align:center;margin-top:100px'>🌐 新窗口 — 输入网址开始浏览</h2>")
        self._view.urlChanged.connect(lambda u: self.setWindowTitle(f"🌐 {u.toString()[:60]}"))
        self._view.titleChanged.connect(lambda t: self.setWindowTitle(f"🌐 {t}"))
        self.setCentralWidget(self._view)
    @property

    def view(self):
        return self._view
# ===== 浏览器页面 =====
# ============================================================
#  BrowserPage - 浏览器页面 (核心)
# ============================================================

class BrowserPage(QWidget):
    """内置浏览器 — 多标签页，使用 PyQt6 QWebEngineView 原生渲染网页"""
    @staticmethod

    def _get_browser_tools():
        """延迟导入 browser_tools（避免循环引用）"""
        import src.tools.browser_tools as bt
        return bt


    def __init__(self, user_info: dict | None = None):
        super().__init__()
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
        # 全局配置：必须在任何 QWebEngineView 创建之前设置
        profile = QWebEngineProfile.defaultProfile()
        # Cookie/存储持久化：固定路径，重启不丢登录态（默认路径随临时目录漂移）
        try:
            from ..tools.cookie_manager import ensure_profile_storage
            ensure_profile_storage()
        except Exception:
            pass
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        title = QLabel("🌐 浏览器")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)
        # ===== URL 输入栏（在标签页上方，标准浏览器布局）=====
        url_layout = QHBoxLayout()
        url_layout.setSpacing(6)
        self._back_btn = QPushButton("⬅")
        self._back_btn.setToolTip("后退")
        self._back_btn.setFixedWidth(36)
        self._back_btn.clicked.connect(self._back_current)
        self._back_btn.setEnabled(False)
        self._back_btn.setStyleSheet("QPushButton { font-size:14px; padding:4px; }")
        url_layout.addWidget(self._back_btn)
        self._forward_btn = QPushButton("➡")
        self._forward_btn.setToolTip("前进")
        self._forward_btn.setFixedWidth(36)
        self._forward_btn.clicked.connect(self._forward_current)
        self._forward_btn.setEnabled(False)
        self._forward_btn.setStyleSheet("QPushButton { font-size:14px; padding:4px; }")
        url_layout.addWidget(self._forward_btn)
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("刷新")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._refresh_current)
        refresh_btn.setStyleSheet("QPushButton { font-size:14px; padding:4px; }")
        url_layout.addWidget(refresh_btn)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("输入网址，按回车打开…")
        self._url_input.returnPressed.connect(self._browse)
        self._url_input.setStyleSheet(f"""

            QLineEdit {{

                background: {THEME['bg_input']};

                color: {THEME['text_primary']};

                border: 1px solid {THEME['accent']};

                border-radius: 6px;

                padding: 8px 12px;

                font-size: 13px;

            }}

            QLineEdit:focus {{

                border-color: {THEME['accent']};

            }}

            QCompleter {{

                background: {THEME['bg_card']};

                border: 1px solid {THEME['border']};

                border-radius: 6px;

            }}

            QCompleter::item {{

                padding: 6px 12px;

                color: {THEME['text_primary']};

                font-size: 12px;

            }}

            QCompleter::item:selected {{

                background: {THEME['accent']};

                color: #000;

            }}

        """)
        url_layout.addWidget(self._url_input, 1)
        go_btn = QPushButton("前往")
        go_btn.clicked.connect(self._browse)
        go_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['accent']};

                color: #000;

                border-radius: 6px;

                padding: 6px 14px;

                font-weight: bold;

                font-size: 12px;

            }}

            QPushButton:hover {{ background: {THEME['accent']}dd; }}

        """)
        url_layout.addWidget(go_btn)
        # 弹出独立窗口按钮
        detach_btn = QPushButton("弹出")
        detach_btn.setToolTip("将当前标签页弹出为独立窗口")
        detach_btn.setFixedWidth(50)
        detach_btn.clicked.connect(self._detach_current_tab)
        detach_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['bg_input']};

                color: {THEME['text_secondary']};

                border: 1px solid {THEME['border']};

                border-radius: 6px;

                font-size: 12px;

                padding: 4px 8px;

            }}

            QPushButton:hover {{

                background: {THEME['accent']};

                color: #000;

            }}

        """)
        url_layout.addWidget(detach_btn)
        # 新标签页按钮
        new_win_btn = QPushButton("新标签")
        new_win_btn.setToolTip("新建标签页 (Ctrl+T)")
        new_win_btn.setFixedWidth(60)
        new_win_btn.clicked.connect(lambda: self._add_tab())
        new_win_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['accent2']};

                color: #fff;

                border: none;

                border-radius: 6px;

                font-size: 12px;

                font-weight: bold;

                padding: 4px 8px;

            }}

            QPushButton:hover {{

                background: {THEME['accent2']}dd;

            }}

        """)
        url_layout.addWidget(new_win_btn)
        layout.addLayout(url_layout)
        # ===== URL 历史记录 (QCompleter) =====
        self._url_history = []
        self._url_completer = QCompleter()
        self._url_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._url_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._url_completer.setMaxVisibleItems(10)
        self._url_model = QStandardItemModel()
        self._url_completer.setModel(self._url_model)
        self._url_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._url_input.setCompleter(self._url_completer)
        # 加载历史记录
        self._load_url_history()
        # ===== 标签页栏 =====
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._tab_widget.setStyleSheet(f"""

            QTabWidget::pane {{

                border: 1px solid {THEME['border']};

                border-radius: 0 0 8px 8px;

                background: transparent;

            }}

            QTabBar::tab {{

                background: {THEME['bg_dark']};

                color: {THEME['text_secondary']};

                padding: 8px 16px;

                border: 1px solid {THEME['border']};

                border-bottom: none;

                margin-right: 2px;

                border-radius: 6px 6px 0 0;

                min-width: 80px;

                max-width: 180px;

            }}

            QTabBar::tab:selected {{

                background: {THEME['bg_card']};

                color: {THEME['accent']};

                font-weight: bold;

            }}

            QTabBar::tab:hover {{

                background: {THEME['hover']};

                color: {THEME['text_primary']};

            }}

            QTabBar::close-button {{

                margin: 3px;

                padding: 0px;

            }}

            QTabBar::close-button:hover {{

                background: {THEME['danger']};

                border-radius: 4px;

            }}

        """)
        layout.addWidget(self._tab_widget, 1)
        # 状态栏
        self._status = QLabel("🟢 就绪 | Ctrl+T 新标签 | Ctrl+W 关标签 | Ctrl+L 地址栏 | 输入网址按回车打开")
        self._status.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 11px;")
        layout.addWidget(self._status)
        # ===== 内部数据结构 =====
        # _tabs: [{'view': QWebEngineView, 'title': str, 'url': str}]
        self._tabs = []
        self._current_view = None
        # 创建第一个标签页
        self._add_tab(url="about:blank", title="新标签页")
        # ===== 全局快捷键（使用 QShortcut 确保任何时候都生效）=====
        from PyQt6.QtGui import QShortcut, QKeySequence
        new_tab_sc = QShortcut(QKeySequence("Ctrl+T"), self)
        new_tab_sc.activated.connect(lambda: self._add_tab())
        new_tab_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        new_tab_n = QShortcut(QKeySequence("Ctrl+N"), self)
        new_tab_n.activated.connect(lambda: self._add_tab())
        new_tab_n.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        close_tab_sc = QShortcut(QKeySequence("Ctrl+W"), self)
        close_tab_sc.activated.connect(self._close_current_tab)
        close_tab_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        focus_url_sc = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_url_sc.activated.connect(lambda: self._url_input.setFocus())
        focus_url_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    # ===== 键盘快捷键辅助方法 =====


    def _close_current_tab(self):
        """关闭当前标签页（Ctrl+W）"""
        idx = self._tab_widget.currentIndex()
        if idx >= 0 and len(self._tabs) > 1:
            self._close_tab(idx)


    def _close_tab_for_view(self, view):
        """根据 QWebEngineView 关闭对应的标签页"""
        # 查找 view 对应的 index
        for i, tab in enumerate(self._tabs):
            if tab["view"] is view:
                if len(self._tabs) > 1:
                    self._close_tab(i)
                return
    # ===== 标签页管理 =====


    def _create_web_view(self):
        """创建一个配置好的 QWebEngineView"""
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        view = QWebEngineView()
        # 连接信号
        view.urlChanged.connect(lambda u, v=view: self._on_view_url_changed(v, u))
        view.titleChanged.connect(lambda t, v=view: self._on_view_title_changed(v, t))
        view.loadStarted.connect(lambda v=view: self._on_view_load_started(v))
        view.loadFinished.connect(lambda ok, v=view: self._on_view_load_finished(v, ok))
        return view


    def _add_tab(self, url="about:blank", title="新标签页"):
        """添加新标签页"""
        view = self._create_web_view()
        idx = self._tab_widget.addTab(view, title)
        tab_data = {"view": view, "title": title, "url": url}
        self._tabs.insert(idx, tab_data)
        self._tab_widget.setCurrentIndex(idx)
        self._update_tab_visibility()
        # 添加自定义关闭按钮 (✕)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setToolTip("关闭标签页")
        close_btn.clicked.connect(lambda checked, v=view: self._close_tab_for_view(v))
        close_btn.setStyleSheet(f"""

            QPushButton {{

                background: transparent;

                color: {THEME['text_muted']};

                border: none;

                border-radius: 4px;

                font-size: 11px;

                font-weight: bold;

                padding: 0;

            }}

            QPushButton:hover {{

                background: {THEME['danger']};

                color: #fff;

            }}

        """)
        self._tab_widget.tabBar().setTabButton(idx, QTabBar.ButtonPosition.RightSide, close_btn)
        # 立即设为当前 view（不等 currentChanged 信号，避免初始化时未触发）
        self._current_view = view
        if url == "about:blank":
            self._url_input.setText("")
        else:
            self._url_input.setText(url)
        self._back_btn.setEnabled(False)
        self._forward_btn.setEnabled(False)
        # 注册到 browser_tools（区分源站/管理后台）
        bt = self._get_browser_tools()
        role = self.property("browser_role") or "source"
        bt.register_web_view(view, role=role)
        if url and url != "about:blank":
            view.load(QUrl(url))


    def _close_tab(self, idx):
        """关闭标签页"""
        if len(self._tabs) <= 1:
            return  # 至少保留一个标签页
        tab = self._tabs[idx]
        view = tab["view"]
        # 断开信号防止残留
        try:
            view.urlChanged.disconnect()
            view.titleChanged.disconnect()
        except Exception:
            pass  # 信号可能未连接，正常
        # 如果是当前活跃的 view，先取消注册
        if view is self._current_view:
            self._current_view = None
        view.deleteLater()
        self._tab_widget.removeTab(idx)
        self._tabs.pop(idx)
        self._update_tab_visibility()


    def _update_tab_visibility(self):
        """只有一个标签时去掉关闭按钮"""
        if self._tab_widget.count() <= 1:
            self._tab_widget.setTabsClosable(False)
        else:
            self._tab_widget.setTabsClosable(True)


    def _detach_current_tab(self):
        """将当前标签页弹出为独立窗口"""
        if not self._tabs or self._tab_widget.count() <= 1:
            return
        idx = self._tab_widget.currentIndex()
        if idx < 0:
            return
        tab = self._tabs[idx]
        url = tab.get("url", "about:blank")
        title = tab.get("title", "独立窗口")
        # 先关闭标签页
        if len(self._tabs) > 1:
            # 切换到其他标签
            if idx > 0:
                self._tab_widget.setCurrentIndex(idx - 1)
            else:
                self._tab_widget.setCurrentIndex(1)
            self._close_tab(idx)
        # 创建新窗口（会自己创建 QWebEngineView）
        win = DetachedBrowserWindow(url=url, title=title)
        # 保存引用防 GC
        if not hasattr(self, '_detached_windows'):
            self._detached_windows = []
        self._detached_windows.append(win)
        win.show()
    # ===== 标签切换 =====


    def _on_tab_changed(self, idx):
        """切换标签页时更新 URL 栏并注册新 view"""
        if idx < 0 or idx >= len(self._tabs):
            return
        tab = self._tabs[idx]
        view = tab["view"]
        self._current_view = view
        # 更新 URL 栏
        current_url = tab.get("url", "")
        if current_url == "about:blank":
            current_url = ""
        self._url_input.setText(current_url)
        # 更新标题
        title_text = tab.get("title", "新标签页")
        self._status.setText(f"📄 {title_text}")
        # 更新前进/后退按钮
        history = view.history()
        self._back_btn.setEnabled(history.canGoBack())
        self._forward_btn.setEnabled(history.canGoForward())
        # 注册到全局，供 browser_tools 使用
        bt = self._get_browser_tools()
        bt.register_web_view(view)
    # ===== View 信号处理 =====


    def _on_view_url_changed(self, view, url):
        url_str = url.toString()
        # 更新对应 tab 的 url
        for tab in self._tabs:
            if tab["view"] is view:
                tab["url"] = url_str
                break
        # 如果是当前 tab，更新 URL 栏
        if view is self._current_view:
            self._url_input.setText(url_str)


    def _on_view_title_changed(self, view, title):
        # 更新对应 tab 的标题
        for i, tab in enumerate(self._tabs):
            if tab["view"] is view:
                tab["title"] = title
                short_title = title[:25] + ("…" if len(title) > 25 else "") if title else "新标签页"
                self._tab_widget.setTabText(i, short_title)
                break
        # 如果是当前 tab，更新状态栏
        if view is self._current_view:
            self._status.setText(f"📄 {title}")


    def _on_view_load_started(self, view):
        if view is self._current_view:
            self._status.setText("⏳ 加载中...")


    def _on_view_load_finished(self, view, ok):
        if view is self._current_view:
            self._status.setText("✅ 加载完成" if ok else "❌ 加载失败")
            history = view.history()
            self._back_btn.setEnabled(history.canGoBack())
            self._forward_btn.setEnabled(history.canGoForward())
        # 注入 JS 修复链接：target=_blank → _self, JS链接 → 真实URL
        if ok:
            fix_js = """

            (function() {

                // 1. 所有 target=_blank 改为 _self

                document.querySelectorAll('a[target="_blank"]').forEach(function(a) {

                    a.target = '_self';

                });

                // 2. javascript:void(0) 链接提取真实 URL

                document.querySelectorAll('a').forEach(function(a) {

                    if (a.href === 'javascript:void(0)' || a.href === 'javascript:void(0);') {

                        var onclick = a.getAttribute('onclick') || '';

                        var m = onclick.match(/(?:location\\.href|window\\.open|window\\.location)\\s*[=\\(]\\s*['"]([^'"]+)['"]/);

                        if (m) a.href = m[1];

                    }

                });

                // 3. 阻止 window.open 弹窗，改为当前页跳转

                window.open = function(url) { if (url) location.href = url; return null; };

            })();

            """
            try:
                view.page().runJavaScript(fix_js)
            except Exception:
                pass
    # ===== 导航操作 =====


    def _browse(self):
        """导航到 URL 栏中输入的网址"""
        url = self._url_input.text().strip()
        if not url:
            return
        # 自动补全协议头
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            self._url_input.setText(url)
        # 确保有可用的 view
        if self._current_view is None or not self._tabs:
            self._add_tab(url=url, title=url[:30])
            return
        # 验证 _current_view 仍然有效
        view_valid = False
        for tab in self._tabs:
            if tab["view"] is self._current_view:
                tab["url"] = url
                view_valid = True
                break
        if not view_valid:
            self._add_tab(url=url, title=url[:30])
            return
        try:
            self._status.setText(f"⏳ 正在加载 {url[:60]}…")
            self._current_view.load(QUrl(url))
            # 记录到历史
            self._add_url_history(url)
        except Exception as e:
            self._status.setText(f"❌ 加载失败: {e}")
    # ===== URL 历史记录管理 =====


    def _get_history_file(self):
        """历史记录文件路径"""
        import os
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "url_history.txt")


    def _load_url_history(self):
        """从文件加载历史记录到 completer"""
        import os
        try:
            path = self._get_history_file()
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
            self._url_history = urls[:100]  # 最多 100 条
            self._url_model.clear()
            for u in self._url_history:
                self._url_model.appendRow(QStandardItem(u))
        except Exception:
            pass


    def _add_url_history(self, url):
        """添加 URL 到历史记录"""
        # 去重：移除已有的相同 URL
        if url in self._url_history:
            self._url_history.remove(url)
        # 添加到最前面
        self._url_history.insert(0, url)
        # 限制 100 条
        self._url_history = self._url_history[:100]
        # 更新 completer model
        self._url_model.clear()
        for u in self._url_history:
            self._url_model.appendRow(QStandardItem(u))
        # 保存到文件
        try:
            import os
            path = self._get_history_file()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self._url_history))
        except Exception:
            pass


    def _refresh_current(self):
        if self._current_view:
            self._current_view.reload()


    def _back_current(self):
        if self._current_view:
            self._current_view.back()


    def _forward_current(self):
        if self._current_view:
            self._current_view.forward()
from .console_panel import ConsoleViewer
from .code_viewer import CodeViewer
from .video_editor.editor_window import VideoEditorPage
# ===== AI 工作台（浏览器 + 对话 左右分屏） =====
# ============================================================
#  ChatBrowserSplitPage - AI对话+浏览器分屏
# ============================================================

class ChatBrowserSplitPage(QWidget):
    """浏览器在左、AI 对话在右，浏览器与控制台一键切换"""
    _switch_signal = pyqtSignal(str)  # 线程安全的切换信号


    def __init__(self, user_info: dict | None = None):
        super().__init__()
        self.setObjectName("workspace_chat")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # ===== 主分屏 =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"""

            QSplitter::handle {{

                background-color: {THEME['accent']}44;

                margin: 4px 0;

                border-radius: 2px;

            }}

            QSplitter::handle:hover {{

                background-color: {THEME['accent']}88;

            }}

        """)
        # 浏览器区 — 4个面板：浏览器 / 源代码 / 视频剪辑器 / 控制台
        self._browser_stack = QStackedWidget()
        self.browser = BrowserPage()
        self.browser.setProperty("browser_role", "source")
        self._browser_stack.addWidget(self.browser)        # 索引 0
        self.code_viewer = CodeViewer()
        self._browser_stack.addWidget(self.code_viewer)     # 索引 1
        self.video_editor = VideoEditorPage()
        self._browser_stack.addWidget(self.video_editor)     # 索引 2
        self.console_viewer = ConsoleViewer()
        self._browser_stack.addWidget(self.console_viewer)  # 索引 3
        # 🔧 代码修改实时面板 — 绑定控制台按钮。默认不自动弹出（防启动打扰），
        # 用户可在面板内点「📌 自动打开」按需开启；控制台按钮可随时手动打开。
        try:
            from .code_change_panel import CodeChangePanel
            self.code_change_panel = CodeChangePanel(self, auto_open=False)
            self.console_viewer.attach_diff_panel(self.code_change_panel)
        except Exception as _panel_err:
            print(f"[console] 实时变更面板初始化失败: {_panel_err}")
        self.chat = ChatPage()
        # ===== 左侧顶部：面板切换按钮栏（4个按钮：浏览器 + 源代码 + 剪辑器 + 控制台）=====
        self._panel_bar = QHBoxLayout()
        self._panel_bar.setContentsMargins(8, 6, 8, 4)
        self._panel_bar.setSpacing(8)
        panel_label = QLabel("📺")
        panel_label.setStyleSheet("font-size: 18px; padding-right: 2px;")
        self._panel_bar.addWidget(panel_label)
        self._btn_browser = self._make_panel_btn("🌐 浏览器", False)
        self._btn_code = self._make_panel_btn("📝 源代码", False)
        self._btn_console = self._make_panel_btn("📟 控制台", True)
        self._btn_video_editor = self._make_panel_btn("🎬 录屏", False)
        self._btn_browser.clicked.connect(lambda: self._switch_panel(0, self._btn_browser))
        self._btn_code.clicked.connect(lambda: self._switch_panel(1, self._btn_code))
        self._btn_video_editor.clicked.connect(lambda: self._switch_panel(2, self._btn_video_editor))
        self._btn_console.clicked.connect(lambda: self._switch_panel(3, self._btn_console))
        self._panel_btns = [self._btn_browser, self._btn_code, self._btn_video_editor, self._btn_console]
        for b in self._panel_btns:
            self._panel_bar.addWidget(b)
        self._panel_bar.addStretch()
        # 左侧面板容器
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addLayout(self._panel_bar)
        # 浏览器/控制台 — 填充剩余空间
        left_layout.addWidget(self._browser_stack, 1)
        splitter.addWidget(left_container)
        splitter.addWidget(self.chat)
        # 默认显示控制台
        self._browser_stack.setCurrentIndex(3)
        splitter.setSizes([700, 540])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        self._admin_window = None
        from src.config.loader import load_config as _load_cfg2
        _cfg2 = _load_cfg2()
        self._admin_url = _cfg2.get("site_7tan", {}).get("base_url", "") + "/"
        # 注册 UI 切换回调 — AI 切浏览器时自动切换面板（通过信号确保主线程安全）
        from src.tools import browser_tools as _bt
        self._switch_signal.connect(self._do_switch_browser)
        _bt._switch_ui_callback = self.switch_browser
        # 首次显示时预加载
        self._initialized = False


    def showEvent(self, event):
        super().showEvent(event)
        if not self._initialized:
            self._initialized = True
        # refresh model list when switching to workspace
        QTimer.singleShot(100, self.chat._load_model_list)


    def _make_panel_btn(self, text: str, active: bool = False):
        """创建面板切换按钮"""
        color = THEME['accent'] if active else THEME['text_secondary']
        bg = f"{THEME['accent']}33" if active else "transparent"
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setFixedHeight(38)
        btn.setStyleSheet(f"""

            QPushButton {{

                background: {bg}; color: {color};

                border: 1px solid {THEME['border']}; border-radius: 4px;

                padding: 4px 18px; font-size: 14px; font-weight: bold;

            }}

            QPushButton:checked {{ background: {THEME['accent']}44; color: {THEME['accent']}; }}

            QPushButton:hover {{ border-color: {THEME['accent']}88; }}

        """)
        return btn


    def _switch_panel(self, index: int, btn: QPushButton):
        """切换左侧面板（0=浏览器, 1=控制台）"""
        self._browser_stack.setCurrentIndex(index)
        for b in self._panel_btns:
            b.setChecked(b is btn)


    def switch_browser(self, target: str):
        """切换显示的浏览器/控制台（线程安全 — 通过信号）"""
        self._switch_signal.emit(target)


    def _do_switch_browser(self, target: str):
        """实际执行切换（仅主线程通过信号触发）"""
        if target == "admin":
            # 切换到浏览器面板，并导航到管理后台
            self._switch_panel(0, self._btn_browser)
            self._navigate_to_admin()
        elif target == "console":
            self._switch_panel(3, self._btn_console)
        else:
            # source / 默认
            self._switch_panel(0, self._btn_browser)


    def _navigate_to_admin(self):
        """在浏览器中打开管理后台（复用已有标签或新建）"""
        if self.browser._current_view is not None:
            current_url = self.browser._current_view.url().toString()
            # 如果当前已经在管理后台，不重复加载
            if self._admin_url in current_url:
                return
        # 打开管理后台
        self.browser._add_tab(url=self._admin_url, title="7tan管理后台")


    def navigate_to_url(self, url: str):
        """在浏览器中打开指定 URL（供侧边栏等外部调用）"""
        self._switch_panel(0, self._btn_browser)
        self.browser._add_tab(url=url, title=url.replace("https://", "").replace("http://", "")[:30])


    def _open_admin_window(self):
        """打开管理后台"""
        self._navigate_to_admin()
        self.switch_browser("admin")


    def _open_source(self):
        """切换到源网站"""
        self.switch_browser("source")
# ===== 统计分析页面 =====
# ============================================================
#  AnalyticsPage - 数据分析
# ============================================================

class AnalyticsPage(QWidget):

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("📈 统计分析")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)
        # 图表
        self._chart_view = QChartView()
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet(f"background-color: {THEME['bg_card']}; border-radius: 10px;")
        layout.addWidget(self._chart_view, 1)
        # 费用统计
        self._cost_label = QLabel("费用统计: 加载中...")
        self._cost_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 13px; padding: 8px;")
        layout.addWidget(self._cost_label)


    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()


    def refresh(self):
        self._worker = ApiWorker("GET", f"{API_BASE}/api/stats/dashboard")
        self._worker.finished.connect(self._on_data)
        self._worker.error.connect(lambda e: logger.error(f"统计加载失败: {e}"))
        self._worker.start()


    def _on_data(self, data):
        self._cost_label.setText(
            f"今日费用: ¥{data.get('today_cost', 0):.4f}  |  "
            f"成功率: {data.get('success_rate', 100)}%  |  "
            f"已发布: {data.get('total_published', 0)}  |  "
            f"进行中: {data.get('in_progress', 0)}"
        )
        # 饼图
        chart = QChart()
        chart.setTitle("资源状态分布")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundBrush(QBrush(QColor(THEME["bg_card"])))
        chart.setTitleBrush(QBrush(QColor(THEME["text_primary"])))
        series = QPieSeries()
        pub = data.get("total_published", 0)
        prog = data.get("in_progress", 0)
        total = pub + prog
        other = max(0, data.get("this_month_new", 0) - pub - prog)
        if total == 0 and other == 0:
            series.append("已发布", 1)
            series.append("处理中", 0)
        else:
            pub_slice = series.append("已发布", max(pub, 0.1))
            prog_slice = series.append("处理中", max(prog, 0.1))
            pub_slice.setBrush(QColor(THEME["success"]))
            prog_slice.setBrush(QColor(THEME["warning"]))
        series.setLabelsVisible(True)
        chart.addSeries(series)
        self._chart_view.setChart(chart)
# ===== 设置页面 =====
# ============================================================
#  SettingsPage - 设置页面
# ============================================================

class SettingsPage(QWidget):

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        self._loaded = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("🔧 设置")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)
        # ===== AI 提供商 → Base URL 映射表 =====
        self._provider_urls = {
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
            "doubao": "https://ark.cn-beijing.volces.com/api/v3",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "moonshot": "https://api.moonshot.cn/v1",
            "mimo": "https://api.xiaomimimo.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "ollama": "http://localhost:11434/v1",
            "custom": "",
        }
        # ===== Tab 页 =====
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""

            QTabWidget::pane {{

                border: 1px solid {THEME['border']};

                border-radius: 8px;

                background: {THEME['bg_card']};

            }}

            QTabBar::tab {{

                background: {THEME['bg_dark']};

                color: {THEME['text_secondary']};

                padding: 10px 24px;

                border: 1px solid {THEME['border']};

                border-bottom: none;

                margin-right: 2px;

                border-top-left-radius: 6px;

                border-top-right-radius: 6px;

                font-size: 14px;

            }}

            QTabBar::tab:selected {{

                background: {THEME['bg_card']};

                color: {THEME['accent']};

                font-weight: bold;

            }}

        """)
        # 五个 Tab
        self._ai_tab = QWidget()
        self._site_tab = QWidget()
        self._oss_tab = QWidget()
        self._plugin_tab = QWidget()
        self._cap_tab = QWidget()
        self._sw_tab = QWidget()
        self._memory_tab = QWidget()
        self._prompt_tab = QWidget()
        self._about_tab = QWidget()
        self._build_ai_tab()
        self._build_site_tab()
        self._build_oss_tab()
        self._build_plugin_tab()
        self._build_capabilities_tab()
        self._build_installed_software_tab()
        self._build_memory_tab()
        self._build_prompt_tab()
        self._build_about_tab()
        self._tabs.addTab(self._ai_tab, "🤖 AI 模型")
        self._tabs.addTab(self._site_tab, "🌐 站点设置")
        self._tabs.addTab(self._oss_tab, "☁️ OSS 存储")
        self._tabs.addTab(self._plugin_tab, "🧩 插件市场")
        self._tabs.addTab(self._cap_tab, "🧠 能力清单")
        self._tabs.addTab(self._sw_tab, "🖥 环境引擎")
        self._tabs.addTab(self._memory_tab, "🧠 记忆系统")
        self._tabs.addTab(self._prompt_tab, "📝 系统提示词")
        self._tabs.addTab(self._about_tab, "ℹ️ 关于7Tan")
        layout.addWidget(self._tabs)
        # 内部状态
        self._ai_configs = {}
        self._active_config = ""
        self._suppress_change = False


    def _keep_worker(self, worker):
        """保持 worker 引用防止 GC — 完成后自动清理"""
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.finished.connect(lambda d, w=worker: self._workers.remove(w) if w in self._workers else None)
        worker.error.connect(lambda e, w=worker: self._workers.remove(w) if w in self._workers else None)


    def showEvent(self, event):
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
        self._load_settings()  # refresh every show
    # =================== AI 模型 Tab ===================

    def _build_ai_tab(self):
        outer = QVBoxLayout(self._ai_tab)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        subtitle = QLabel("管理多个 AI 大模型配置，一键切换当前使用的模型。保存后即时生效。")
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        outer.addWidget(subtitle)
        # --- 左右分栏 ---
        split = QHBoxLayout()
        split.setSpacing(16)
        # 左侧：配置列表
        left = QVBoxLayout()
        left.setSpacing(8)
        left_label = QLabel("已保存的模型")
        left_label.setStyleSheet(f"font-weight: bold; color: {THEME['accent']}; font-size: 13px;")
        left.addWidget(left_label)
        self._config_list = QListWidget()
        self._config_list.setFixedWidth(200)
        self._config_list.setMinimumHeight(260)
        self._config_list.currentRowChanged.connect(self._on_config_selected)
        self._config_list.setStyleSheet(f"""

            QListWidget {{

                background: {THEME['bg_input']};

                border: 1px solid {THEME['border']};

                border-radius: 6px;

                color: {THEME['text_primary']};

                font-size: 13px;

            }}

            QListWidget::item {{

                padding: 10px 14px;

                border-bottom: 1px solid {THEME['border']};

            }}

            QListWidget::item:selected {{

                background: {THEME['accent2']};

                color: white;

            }}

        """)
        left.addWidget(self._config_list)
        # 配置操作按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)


        def _make_btn(text, tooltip, bg_color, hover_color):
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(34)
            btn.setMinimumWidth(80)
            btn.setStyleSheet(f"""

                QPushButton {{ background: {bg_color}; color: white; border-radius: 8px; font-size: 13px; border: none; padding: 6px 12px; }}

                QPushButton:hover {{ background: {hover_color}; }}

            """)
            return btn
        add_btn = _make_btn("＋ 新建", "新建模型配置", THEME['success'], "#059669")
        add_btn.clicked.connect(self._add_config)
        btn_row.addWidget(add_btn)
        del_btn = _make_btn("✕ 删除", "删除选中配置", THEME['danger'], "#dc2626")
        del_btn.clicked.connect(self._delete_config)
        btn_row.addWidget(del_btn)
        active_btn = _make_btn("⭐ 启用", "设为当前使用的模型", THEME['warning'], "#d97706")
        active_btn.clicked.connect(self._set_active_config)
        btn_row.addWidget(active_btn)
        btn_row.addStretch()
        left.addLayout(btn_row)
        split.addLayout(left)
        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {THEME['border']};")
        split.addWidget(sep)
        # 右侧：编辑表单
        right = QVBoxLayout()
        right.setSpacing(12)
        right_title = QLabel("编辑模型配置")
        right_title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {THEME['text_primary']};")
        right.addWidget(right_title)
        form = QFormLayout()
        form.setSpacing(10)
        self._ai_name = QLineEdit()
        self._ai_name.setPlaceholderText("如 deepseek、openai-gpt4、qwen-local")
        self._ai_name.setMinimumHeight(32)
        self._ai_provider = QComboBox()
        self._ai_provider.addItems(list(self._provider_urls.keys()))
        self._ai_provider.currentTextChanged.connect(self._on_provider_changed)
        self._ai_provider.setMinimumHeight(32)
        self._ai_model = QComboBox()
        self._ai_model.setEditable(True)
        self._ai_model.addItems(["deepseek-chat", "deepseek-reasoner", "gpt-4o", "gpt-4o-mini", "qwen-max", "glm-4-plus", "kimi-k3"])
        self._ai_model.setMinimumHeight(32)
        self._ai_key = QLineEdit()
        self._ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._ai_key.setPlaceholderText("sk-...")
        self._ai_key.setMinimumHeight(32)
        # API Key 显示/隐藏切换按钮
        self._ai_key_toggle = QPushButton("显示")
        self._ai_key_toggle.setFixedSize(42, 32)
        self._ai_key_toggle.setToolTip("显示/隐藏 API Key")
        self._ai_key_toggle.setCheckable(True)
        self._ai_key_toggle.clicked.connect(self._toggle_api_key_visibility)
        self._ai_key_toggle.setStyleSheet(f"""

            QPushButton {{ background: {THEME['bg_input']}; border: 1px solid {THEME['border']};

                border-radius: 6px; color: {THEME['text_secondary']}; font-size: 11px; padding: 2px 6px; }}

            QPushButton:checked {{ background: {THEME['accent']}; color: #000; font-weight: bold; }}

            QPushButton:hover {{ border-color: {THEME['accent']}; }}

        """)
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_row.addWidget(self._ai_key, 1)
        key_row.addWidget(self._ai_key_toggle)
        self._ai_base = QLineEdit()
        self._ai_base.setMinimumHeight(32)
        form.addRow("配置名称:", self._ai_name)
        form.addRow("AI 提供商:", self._ai_provider)
        form.addRow("模型名称:", self._ai_model)
        form.addRow("API Key:", key_row)
        form.addRow("Base URL:", self._ai_base)
        right.addLayout(form)
        # 提示文字
        hint = QLabel("💡 切换提供商时 Base URL 会自动填入。如需自定义，手动修改即可。")
        hint.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 11px; padding: 4px 0;")
        right.addWidget(hint)
        right.addStretch()
        # 保存当前模型按钮
        save_btn = QPushButton("💾 保存此模型配置")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_ai_config)
        save_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['accent']}; color: #000; border: none;

                border-radius: 6px; font-size: 14px; font-weight: bold;

            }}

            QPushButton:hover {{ background: #33ddff; }}

        """)
        right.addWidget(save_btn)
        split.addLayout(right, 1)
        outer.addLayout(split)
        # ===== 视觉AI模型（增强桌面机器人视力）=====
        vis_box = QFrame()
        vis_box.setStyleSheet(f"QFrame {{ background: {THEME['bg_dark']}; border: 1px solid {THEME['border']}; border-radius: 8px; }}")
        vis_lay = QVBoxLayout(vis_box)
        vis_lay.setContentsMargins(14, 12, 14, 12)
        vis_lay.setSpacing(8)
        vis_title = QLabel("👁️ 视觉AI模型（增强桌面机器人视力）")
        vis_title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {THEME['accent']};")
        vis_lay.addWidget(vis_title)
        vis_hint = QLabel("为了增加软件的视觉功能（看懂屏幕·识别按钮·发现弹窗），请添加一个视觉AI模型，"
                          "推荐「GLM-4V-Flash」（智谱AI，免费额度，国内直连）。"
                          "未配置时桌面机器人自动使用本地离线识别（RapidOCR 双引擎）。")
        vis_hint.setWordWrap(True)
        vis_hint.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px; "
                               f"background: {THEME['bg_input']}; border-radius: 6px; padding: 8px 10px;")
        vis_lay.addWidget(vis_hint)
        vis_form = QFormLayout()
        vis_form.setSpacing(8)
        self._vis_key = QLineEdit()
        self._vis_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._vis_key.setPlaceholderText("sk-...（智谱开放平台 open.bigmodel.cn 获取）")
        self._vis_key.setMinimumHeight(32)
        self._vis_key_toggle = QPushButton("显示")
        self._vis_key_toggle.setFixedSize(42, 32)
        self._vis_key_toggle.setToolTip("显示/隐藏视觉 API Key")
        self._vis_key_toggle.setCheckable(True)
        self._vis_key_toggle.clicked.connect(self._toggle_vision_key_visibility)
        self._vis_key_toggle.setStyleSheet(f"""
            QPushButton {{ background: {THEME['bg_input']}; border: 1px solid {THEME['border']};
                border-radius: 6px; color: {THEME['text_secondary']}; font-size: 11px; padding: 2px 6px; }}
            QPushButton:checked {{ background: {THEME['accent']}; color: #000; font-weight: bold; }}
            QPushButton:hover {{ border-color: {THEME['accent']}; }}
        """)
        vis_key_row = QHBoxLayout()
        vis_key_row.setSpacing(6)
        vis_key_row.addWidget(self._vis_key, 1)
        vis_key_row.addWidget(self._vis_key_toggle)
        self._vis_base = QLineEdit("https://open.bigmodel.cn/api/paas/v4")
        self._vis_base.setMinimumHeight(32)
        self._vis_model = QLineEdit("glm-4v-flash")
        self._vis_model.setMinimumHeight(32)
        vis_form.addRow("视觉 API Key:", vis_key_row)
        vis_form.addRow("Base URL:", self._vis_base)
        vis_form.addRow("模型名称:", self._vis_model)
        vis_lay.addLayout(vis_form)
        vis_save = QPushButton("💾 保存视觉模型")
        vis_save.setFixedHeight(34)
        vis_save.clicked.connect(self._save_vision_config)
        vis_save.setStyleSheet(f"""
            QPushButton {{ background: {THEME['accent2']}; color: white; border: none;
                border-radius: 6px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background: {THEME['accent']}; color: #000; }}
        """)
        vis_lay.addWidget(vis_save)
        outer.addWidget(vis_box)
        # 初始化默认 URL
        self._on_provider_changed(self._ai_provider.currentText())
    # =================== 站点设置 Tab ===================

    def _build_site_tab(self):
        layout = QVBoxLayout(self._site_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        subtitle = QLabel("7坛管理后台登录信息。修改后保存即可生效，无需重启。")
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        layout.addWidget(subtitle)
        group = QGroupBox("站点配置")
        group.setStyleSheet(f"""

            QGroupBox {{

                color: {THEME['text_primary']}; font-weight: bold; font-size: 14px;

                border: 1px solid {THEME['border']}; border-radius: 8px; margin-top: 12px; padding-top: 20px;

            }}

            QGroupBox::title {{ subcontrol-origin: margin; left: 16px; padding: 0 8px; }}

        """)
        form = QFormLayout(group)
        form.setSpacing(12)
        self._site_url = QLineEdit()
        self._site_url.setPlaceholderText("https://你的域名/api")
        self._site_user = QLineEdit()
        self._site_pass = QLineEdit()
        self._site_pass.setEchoMode(QLineEdit.EchoMode.Password)
        # 密码显示/隐藏按钮
        self._site_pass_toggle = QPushButton("显示")
        self._site_pass_toggle.setFixedSize(42, 32)
        self._site_pass_toggle.setToolTip("显示/隐藏密码")
        self._site_pass_toggle.setCheckable(True)
        self._site_pass_toggle.clicked.connect(self._toggle_site_pass_visibility)
        self._site_pass_toggle.setStyleSheet(f"""

            QPushButton {{ background: {THEME['bg_input']}; border: 1px solid {THEME['border']};

                border-radius: 6px; color: {THEME['text_secondary']}; font-size: 11px; padding: 2px 6px; }}

            QPushButton:checked {{ background: {THEME['accent']}; color: #000; font-weight: bold; }}

            QPushButton:hover {{ border-color: {THEME['accent']}; }}

        """)
        pass_row = QHBoxLayout()
        pass_row.setSpacing(6)
        pass_row.addWidget(self._site_pass, 1)
        pass_row.addWidget(self._site_pass_toggle)
        self._publish_interval = QSpinBox()
        self._publish_interval.setRange(1, 1440)
        self._publish_interval.setValue(30)
        self._publish_interval.setSuffix(" 分钟")
        for w in [self._site_url, self._site_user, self._site_pass]:
            w.setMinimumHeight(32)
        form.addRow("站点地址:", self._site_url)
        form.addRow("用户名:", self._site_user)
        form.addRow("密码:", pass_row)
        form.addRow("发布间隔:", self._publish_interval)
        layout.addWidget(group)
        layout.addStretch()
        save_btn = QPushButton("💾 保存站点设置")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_site_config)
        save_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['accent']}; color: #000; border: none;

                border-radius: 6px; font-size: 14px; font-weight: bold;

            }}

            QPushButton:hover {{ background: #33ddff; }}

        """)
        layout.addWidget(save_btn)
    # =================== OSS 存储 Tab ===================

    def _build_oss_tab(self):
        layout = QVBoxLayout(self._oss_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        subtitle = QLabel("云存储用于上传安装包。修改后保存即可生效。")
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        layout.addWidget(subtitle)
        group = QGroupBox("OSS 配置")
        group.setStyleSheet(f"""

            QGroupBox {{

                color: {THEME['text_primary']}; font-weight: bold; font-size: 14px;

                border: 1px solid {THEME['border']}; border-radius: 8px; margin-top: 12px; padding-top: 20px;

            }}

            QGroupBox::title {{ subcontrol-origin: margin; left: 16px; padding: 0 8px; }}

        """)
        form = QFormLayout(group)
        form.setSpacing(12)
        self._oss_bucket = QLineEdit()
        self._oss_bucket.setPlaceholderText("my-bucket")
        self._oss_endpoint = QLineEdit()
        self._oss_endpoint.setPlaceholderText("oss-cn-shanghai.aliyuncs.com")
        self._oss_key = QLineEdit()
        self._oss_key.setPlaceholderText("LTAI...")
        self._oss_secret = QLineEdit()
        self._oss_secret.setEchoMode(QLineEdit.EchoMode.Password)
        for w in [self._oss_bucket, self._oss_endpoint, self._oss_key, self._oss_secret]:
            w.setMinimumHeight(32)
        # AccessKey 显示/隐藏按钮
        self._oss_key_toggle = QPushButton("显示")
        self._oss_key_toggle.setFixedSize(42, 32)
        self._oss_key_toggle.setToolTip("显示/隐藏 AccessKey")
        self._oss_key_toggle.setCheckable(True)
        self._oss_key_toggle.clicked.connect(self._toggle_oss_key_visibility)
        self._oss_key_toggle.setStyleSheet(f"""

            QPushButton {{ background: {THEME['bg_input']}; border: 1px solid {THEME['border']};

                border-radius: 6px; color: {THEME['text_secondary']}; font-size: 11px; padding: 2px 6px; }}

            QPushButton:checked {{ background: {THEME['accent']}; color: #000; font-weight: bold; }}

            QPushButton:hover {{ border-color: {THEME['accent']}; }}

        """)
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_row.addWidget(self._oss_key, 1)
        key_row.addWidget(self._oss_key_toggle)
        # SecretKey 显示/隐藏按钮
        self._oss_secret_toggle = QPushButton("显示")
        self._oss_secret_toggle.setFixedSize(42, 32)
        self._oss_secret_toggle.setToolTip("显示/隐藏 SecretKey")
        self._oss_secret_toggle.setCheckable(True)
        self._oss_secret_toggle.clicked.connect(self._toggle_oss_secret_visibility)
        self._oss_secret_toggle.setStyleSheet(f"""

            QPushButton {{ background: {THEME['bg_input']}; border: 1px solid {THEME['border']};

                border-radius: 6px; color: {THEME['text_secondary']}; font-size: 11px; padding: 2px 6px; }}

            QPushButton:checked {{ background: {THEME['accent']}; color: #000; font-weight: bold; }}

            QPushButton:hover {{ border-color: {THEME['accent']}; }}

        """)
        secret_row = QHBoxLayout()
        secret_row.setSpacing(6)
        secret_row.addWidget(self._oss_secret, 1)
        secret_row.addWidget(self._oss_secret_toggle)
        form.addRow("Bucket:", self._oss_bucket)
        form.addRow("Endpoint:", self._oss_endpoint)
        form.addRow("AccessKey:", key_row)
        form.addRow("SecretKey:", secret_row)
        layout.addWidget(group)
        layout.addStretch()
        save_btn = QPushButton("💾 保存 OSS 设置")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_oss_config)
        save_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['accent']}; color: #000; border: none;

                border-radius: 6px; font-size: 14px; font-weight: bold;

            }}

            QPushButton:hover {{ background: #33ddff; }}

        """)
        layout.addWidget(save_btn)
    # =================== 事件处理 ===================


    def _on_provider_changed(self, provider):
        default_url = self._provider_urls.get(provider, "")
        if default_url:
            self._ai_base.setText(default_url)


    def _toggle_api_key_visibility(self, checked):
        """切换 API Key 显示/隐藏"""
        item = self._config_list.currentItem()
        if not item:
            return
        key_name = item.data(Qt.ItemDataRole.UserRole)
        if checked:
            # 显示：优先从数据库获取真实密钥（AI 配置存在数据库，不在 YAML）
            real_key = ""
            try:
                from src.database.db import get_ai_config_by_key
                cfg = get_ai_config_by_key(key_name, mask_secrets=False)
                if cfg:
                    real_key = cfg.get("api_key", "")
            except Exception:
                pass
            # fallback：如果数据库没拿到，尝试从 load_config 解析环境变量引用
            if not real_key:
                import re
                from src.config.loader import load_config
                config = load_config()
                raw_key = config.get("ai", {}).get("configs", {}).get(key_name, {}).get("api_key", "")
                real_key = re.sub(r'\$\{(\w+)\}', lambda m: _os.environ.get(m.group(1), m.group(0)), raw_key)
            if real_key:
                self._ai_key.setText(real_key)
                # 同步到内存缓存，防止后续操作覆盖用户输入
                if key_name in self._ai_configs:
                    self._ai_configs[key_name]["api_key"] = real_key
            self._ai_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self._ai_key_toggle.setText("隐藏")
        else:
            # 隐藏：仅切换密码模式，不覆盖输入框内容（修复：之前从脱敏缓存覆盖导致用户输入丢失）
            self._ai_key.setEchoMode(QLineEdit.EchoMode.Password)
            self._ai_key_toggle.setText("显示")


    def _on_config_selected(self, row):
        if self._suppress_change:
            return
        if row < 0:
            return
        key = self._config_list.item(row).data(Qt.ItemDataRole.UserRole)
        cfg = self._ai_configs.get(key, {})
        self._suppress_change = True
        self._ai_name.setText(key)
        self._ai_provider.setCurrentText(cfg.get("provider", "deepseek"))
        self._ai_model.setCurrentText(cfg.get("model", ""))
        self._ai_base.setText(cfg.get("base_url", ""))
        self._ai_key.setText(cfg.get("api_key", ""))
        self._refresh_config_list()
        self._suppress_change = False


    def _refresh_config_list(self):
        self._suppress_change = True
        current_key = self._config_list.currentItem().data(Qt.ItemDataRole.UserRole) if self._config_list.currentItem() else None
        self._config_list.blockSignals(True)
        self._config_list.clear()
        for key, cfg in self._ai_configs.items():
            label = f"⭐ {key}" if key == self._active_config else f"  {key}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._config_list.addItem(item)
            if key == current_key:
                self._config_list.setCurrentItem(item)
        self._config_list.blockSignals(False)
        # 如果列表为空，不创建兜底默认配置（避免覆盖真实数据）
        if self._config_list.count() == 0:
            self._ai_configs = {"deepseek": {
                "provider": "deepseek", "model": "",
                "base_url": "https://api.deepseek.com/v1", "api_key": ""
            }}
            self._active_config = "deepseek"
            self._refresh_config_list()
        self._suppress_change = False


    def _add_config(self):
        name, ok = QInputDialog.getText(self, "新建模型配置", "请输入配置名称（英文标识）:", text="new-model")
        if not ok or not name.strip():
            return
        name = name.strip().lower().replace(" ", "-")
        if name in self._ai_configs:
            QMessageBox.warning(self, "名称重复", f"「{name}」已存在，请换一个名称。")
            return
        self._ai_configs[name] = {"provider": "deepseek", "model": "", "base_url": "https://api.deepseek.com/v1", "api_key": ""}
        self._refresh_config_list()
        for i in range(self._config_list.count()):
            if self._config_list.item(i).data(Qt.ItemDataRole.UserRole) == name:
                self._config_list.setCurrentRow(i)
                break


    def _delete_config(self):
        item = self._config_list.currentItem()
        if not item:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if len(self._ai_configs) <= 1:
            QMessageBox.warning(self, "无法删除", "至少保留一个 AI 配置！")
            return
        reply = QMessageBox.question(self, "确认删除", f"确定删除配置「{key}」吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self._ai_configs[key]
        if key == self._active_config:
            self._active_config = next(iter(self._ai_configs.keys()))
        self._refresh_config_list()
        # 同步删除到后端数据库（否则重启后配置会从数据库恢复）
        worker = ApiWorker("PUT", f"{API_BASE}/api/settings",
                           {"ai": {"active": self._active_config, "deleted": [key]}})
        worker.finished.connect(lambda d, k=key: QMessageBox.information(self, "成功", f"配置「{k}」已删除"))
        worker.error.connect(lambda e, k=key: self._on_delete_config_error(e, k))
        worker.start()
        self._keep_worker(worker)

    def _on_delete_config_error(self, error, key):
        QMessageBox.warning(self, "错误", f"删除配置「{key}」失败: {error}\n已恢复原列表，请重试。")
        self._load_settings()

    def _set_active_config(self):
        item = self._config_list.currentItem()
        if not item:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        self._active_config = key
        self._refresh_config_list()
        # 即时保存 active 切换
        self._save_ai_active_only()
        QMessageBox.information(self, "已切换", f"当前使用: ⭐ {key}")


    def _save_ai_active_only(self):
        """仅保存 active 切换（不触发全量保存）"""
        self._post_json("PUT", "/api/settings", {"ai": {"active": self._active_config}},
                        ok_msg=None, err_msg="激活切换失败")


    def _load_settings(self):
        self._worker = ApiWorker("GET", f"{API_BASE}/api/settings")
        self._worker.finished.connect(self._on_settings_loaded)
        self._worker.error.connect(lambda e: logger.error(f"设置加载失败: {e}"))
        self._worker.start()


    def _on_settings_loaded(self, data):
        settings = data.get("settings", {})
        ai = settings.get("ai", {})
        if "configs" not in ai and "provider" in ai:
            ai = {"active": ai.get("provider", "deepseek"), "configs": {
                ai.get("provider", "deepseek"): {
                    "provider": ai.get("provider", "deepseek"),
                    "model": ai.get("model", ""),
                    "base_url": ai.get("api_base", ai.get("base_url", "")),
                    "api_key": ai.get("api_key", ""),
                }
            }}
        self._ai_configs = ai.get("configs", {})
        self._active_config = ai.get("active", next(iter(self._ai_configs.keys())) if self._ai_configs else "deepseek")
        if not self._ai_configs:
            self._ai_configs = {"deepseek": {
                "provider": "deepseek", "model": "",
                "base_url": "https://api.deepseek.com/v1", "api_key": ""
            }}
            self._active_config = "deepseek"
        self._config_list.blockSignals(True)
        self._config_list.clear()
        for key in self._ai_configs:
            label = f"⭐ {key}" if key == self._active_config else f"  {key}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._config_list.addItem(item)
        self._config_list.setCurrentRow(0)
        self._config_list.blockSignals(False)
        self._suppress_change = False
        # 手动触发选中事件，填充表单（因为 blockSignals 阻止了信号）
        self._on_config_selected(0)
        # 视觉AI模型（增强桌面机器人视力）
        vision = (settings.get("ai") or {}).get("vision") or {}
        self._vis_key.setText(vision.get("api_key", ""))
        self._vis_base.setText(vision.get("base_url", "https://open.bigmodel.cn/api/paas/v4"))
        self._vis_model.setText(vision.get("model", "glm-4v-flash"))
        site = settings.get("site_7tan", {})
        self._site_url.setText(site.get("base_url", ""))
        self._site_user.setText(site.get("username", ""))
        self._publish_interval.setValue(site.get("publish_delay_min", 30))
        self._site_pass.setText(site.get("password", ""))
        # 重置密码显示/隐藏按钮状态
        self._site_pass_toggle.setChecked(False)
        self._site_pass.setEchoMode(QLineEdit.EchoMode.Password)
        oss = settings.get("oss", {})
        self._oss_bucket.setText(oss.get("bucket", ""))
        self._oss_endpoint.setText(oss.get("endpoint", oss.get("region", "")))
        self._oss_key.setText(oss.get("access_key", ""))
        self._oss_secret.setText(oss.get("secret_key", ""))
        # 重置 OSS 密钥显示/隐藏按钮
        self._oss_key_toggle.setChecked(False)
        self._oss_secret_toggle.setChecked(False)
        self._oss_secret.setEchoMode(QLineEdit.EchoMode.Password)


    def _save_ai_config(self):
        """只保存当前编辑的 AI 模型配置（不发送其他配置，防止跨配置污染）"""
        item = self._config_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个配置。")
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        old = self._ai_configs.get(key, {})
        self._ai_configs[key] = {
            "provider": self._ai_provider.currentText(),
            "model": self._ai_model.currentText(),
            "base_url": self._ai_base.text(),
            "api_key": self._ai_key.text() if self._ai_key.text() and self._ai_key.text() != "••••••••"
                      else old.get("api_key", ""),
            # 保留高级参数，防止保存时被默认值覆盖
            "context_window": old.get("context_window", 128000),
            "max_tokens": old.get("max_tokens", 16384),
            "temperature": old.get("temperature", 0.25),
            "extra_config": old.get("extra_config"),
        }
        # 只发送当前编辑的配置，避免其他模型的配置被覆盖
        payload = {
            "ai": {
                "active": self._active_config,
                "configs": {key: self._ai_configs[key]},
            }
        }
        self._post_json("PUT", "/api/settings", payload, ok_msg=f"模型「{key}」已保存！")


    def _toggle_vision_key_visibility(self, checked):
        """切换视觉模型 API Key 显示/隐藏 — 显示时从本地配置加载真实密钥"""
        if checked:
            try:
                from src.config.loader import load_config
                config = load_config()
                real_key = (config.get("ai") or {}).get("vision", {}).get("api_key", "")
                if real_key:
                    self._vis_key.setText(real_key)
            except Exception:
                pass
            self._vis_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self._vis_key_toggle.setText("隐藏")
        else:
            self._vis_key.setEchoMode(QLineEdit.EchoMode.Password)
            self._vis_key_toggle.setText("显示")

    def _save_vision_config(self):
        """保存视觉AI模型配置（GLM-4V-Flash 等），增强桌面机器人视力"""
        vis = {}
        key = self._vis_key.text().strip()
        if key and "••" not in key and "***" not in key:
            vis["api_key"] = key
        base = self._vis_base.text().strip()
        if base:
            vis["base_url"] = base
        model = self._vis_model.text().strip()
        if model:
            vis["model"] = model
        if not vis:
            QMessageBox.warning(self, "提示", "请填写视觉模型配置（API Key / Base URL / 模型名称至少一项）。")
            return
        self._post_json("PUT", "/api/settings", {"ai": {"vision": vis}}, ok_msg="视觉模型已保存！桌面机器人视力增强已生效。")

    def _toggle_site_pass_visibility(self, checked):
        """切换站点密码显示/隐藏 — 显示时从本地配置加载真实密码"""
        if checked:
            from src.config.loader import load_config
            config = load_config()
            real_pass = config.get("site_7tan", {}).get("password", "")
            if real_pass:
                self._site_pass.setText(real_pass)
            self._site_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self._site_pass_toggle.setText("隐藏")
        else:
            self._site_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self._site_pass_toggle.setText("显示")


    def _save_site_config(self):
        """只保存站点设置"""
        payload = {
            "site_7tan": {
                "base_url": self._site_url.text(),
                "login_url": self._site_url.text() + "/login.php",
                "username": self._site_user.text(),
                "publish_delay_min": self._publish_interval.value(),
            },
        }
        if self._site_pass.text() and self._site_pass.text() != "••••••••":
            payload["site_7tan"]["password"] = self._site_pass.text()
        self._post_json("PUT", "/api/settings", payload, ok_msg="站点设置已保存！")


    def _toggle_oss_key_visibility(self, checked):
        if checked:
            from src.config.loader import load_config
            config = load_config()
            real_key = config.get("oss", {}).get("access_key", "")
            if real_key:
                self._oss_key.setText(real_key)
            self._oss_key_toggle.setText("隐藏")
        else:
            self._oss_key_toggle.setText("显示")


    def _toggle_oss_secret_visibility(self, checked):
        if checked:
            from src.config.loader import load_config
            config = load_config()
            real_secret = config.get("oss", {}).get("secret_key", "")
            if real_secret:
                self._oss_secret.setText(real_secret)
            self._oss_secret.setEchoMode(QLineEdit.EchoMode.Normal)
            self._oss_secret_toggle.setText("隐藏")
        else:
            self._oss_secret.setEchoMode(QLineEdit.EchoMode.Password)
            self._oss_secret_toggle.setText("显示")


    def _save_oss_config(self):
        """只保存 OSS 设置"""
        payload = {
            "oss": {
                "bucket": self._oss_bucket.text(),
                "endpoint": self._oss_endpoint.text(),
                "region": self._oss_endpoint.text(),
            },
        }
        if self._oss_key.text() and self._oss_key.text() != "••••••••":
            payload["oss"]["access_key"] = self._oss_key.text()
        if self._oss_secret.text() and self._oss_secret.text() != "••••••••":
            payload["oss"]["secret_key"] = self._oss_secret.text()
        self._post_json("PUT", "/api/settings", payload, ok_msg="OSS 设置已保存！")
    # =================== 插件市场 Tab ===================

    def show_plugin_tab(self):
        """侧边栏「插件市场」入口 → 定位到插件市场 Tab"""
        if hasattr(self, "_plugin_tab"):
            self._tabs.setCurrentWidget(self._plugin_tab)


    def _build_plugin_tab(self):
        layout = QVBoxLayout(self._plugin_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        subtitle = QLabel("选择安装需要的功能插件，安装后 AI 将获得新能力。已安装的插件在启动时自动加载。")
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        # 刷新行
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        refresh_btn = QPushButton(" 刷新插件")
        refresh_btn.setIcon(create_refresh_icon(34))
        refresh_btn.setIconSize(QSize(20, 20))
        refresh_btn.setFixedHeight(32)
        refresh_btn.setToolTip("重新扫描并刷新本地插件列表")
        refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh_btn.clicked.connect(self._refresh_plugins)
        refresh_btn.setStyleSheet(f"""

            QPushButton {{

                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,

                    stop:0 {THEME['accent2']}, stop:1 {THEME['accent']});

                color: #fff; border: 1px solid {THEME['accent']}66;

                border-radius: 8px; padding: 4px 16px 4px 10px;

                font-size: 13px; font-weight: bold;

            }}

            QPushButton:hover {{

                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,

                    stop:0 {THEME['accent2']}dd, stop:1 {THEME['accent']}dd);

            }}

            QPushButton:pressed {{

                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,

                    stop:0 {THEME['accent']}, stop:1 {THEME['accent2']});

            }}

        """)
        top_row.addWidget(refresh_btn)
        layout.addLayout(top_row)
        # 插件列表
        self._plugin_list = QListWidget()
        self._plugin_list.setMinimumHeight(300)
        self._plugin_list.currentRowChanged.connect(self._on_plugin_selected)
        self._plugin_list.setStyleSheet(f"""

            QListWidget {{ background: {THEME['bg_card']}; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 8px; font-size: 13px; }}

            QListWidget::item {{ padding: 14px 18px; border-bottom: 1px solid {THEME['border']}; }}

            QListWidget::item:hover {{ background: {THEME['hover']}; }}

            QListWidget::item:selected {{ background: {THEME['accent']}33; }}

        """)
        layout.addWidget(self._plugin_list, 1)
        # 详情区
        detail_group = QGroupBox("插件详情")
        detail_group.setStyleSheet(f"""

            QGroupBox {{ color: {THEME['text_primary']}; font-weight: bold; font-size: 13px;

                border: 1px solid {THEME['border']}; border-radius: 8px; margin-top: 8px; padding-top: 18px; }}

            QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 8px; }}

        """)
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.setSpacing(6)
        self._detail_label = QLabel("选择一个插件查看详情")
        self._detail_label.setWordWrap(True)
        self._detail_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px; padding: 4px;")
        self._detail_label.setMinimumHeight(60)
        detail_layout.addWidget(self._detail_label)
        layout.addWidget(detail_group)
        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._install_btn = QPushButton("📥 安装")
        self._install_btn.setFixedHeight(36)
        self._install_btn.setFixedWidth(100)
        self._install_btn.clicked.connect(self._install_plugin)
        self._install_btn.setStyleSheet(f"""

            QPushButton {{ background: {THEME['success']}; color: #fff; border: none;

                border-radius: 8px; font-size: 14px; font-weight: bold; }}

            QPushButton:hover {{ background: #059669; }}

        """)
        btn_row.addWidget(self._install_btn)
        self._uninstall_btn = QPushButton("🗑️ 卸载")
        self._uninstall_btn.setFixedHeight(36)
        self._uninstall_btn.setFixedWidth(100)
        self._uninstall_btn.clicked.connect(self._uninstall_plugin)
        self._uninstall_btn.setStyleSheet(f"""

            QPushButton {{ background: {THEME['danger']}; color: #fff; border: none;

                border-radius: 8px; font-size: 14px; font-weight: bold; }}

            QPushButton:hover {{ background: #dc2626; }}

        """)
        btn_row.addWidget(self._uninstall_btn)
        btn_row.addStretch()
        # 一键安装全部
        install_all_btn = QPushButton("⚡ 一键安装全部")
        install_all_btn.setFixedHeight(36)
        install_all_btn.setFixedWidth(130)
        install_all_btn.clicked.connect(self._install_all_plugins)
        install_all_btn.setStyleSheet(f"""

            QPushButton {{ background: {THEME['accent2']}; color: #fff; border: none;

                border-radius: 8px; font-size: 13px; font-weight: bold; }}

            QPushButton:hover {{ background: {THEME['accent2']}dd; }}

        """)
        btn_row.addWidget(install_all_btn)
        layout.addLayout(btn_row)
        # 状态栏
        self._plugin_status = QLabel("")
        self._plugin_status.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        layout.addWidget(self._plugin_status)
        # ── 授权管理（付费插件激活）──
        self._license_group = QGroupBox("🔑 授权管理（付费插件）")
        self._license_group.setStyleSheet(f"""

            QGroupBox {{ color: {THEME['text_primary']}; font-weight: bold; font-size: 13px;

                border: 1px solid {THEME['border']}; border-radius: 8px; margin-top: 8px; padding-top: 18px; }}

            QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 8px; }}

        """)
        license_layout = QVBoxLayout(self._license_group)
        license_layout.setSpacing(8)
        license_layout.setContentsMargins(12, 12, 12, 12)
        self._license_status_label = QLabel("")
        self._license_status_label.setWordWrap(True)
        self._license_status_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        license_layout.addWidget(self._license_status_label)
        license_input_row = QHBoxLayout()
        license_input_row.setSpacing(8)
        self._license_input = QLineEdit()
        self._license_input.setPlaceholderText("粘贴购买获得的授权码（指纹.签名）")
        self._license_input.setStyleSheet(f"""

            QLineEdit {{ background: {THEME['bg_input']}; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 6px; padding: 6px 10px; font-size: 12px; }}

        """)
        license_input_row.addWidget(self._license_input, 1)
        self._license_activate_btn = QPushButton("✅ 激活")
        self._license_activate_btn.setFixedHeight(32)
        self._license_activate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._license_activate_btn.clicked.connect(self._activate_plugin_license)
        self._license_activate_btn.setStyleSheet(f"""

            QPushButton {{ background: {THEME['success']}; color: #fff; border: none;

                border-radius: 6px; padding: 4px 18px; font-size: 13px; font-weight: bold; }}

            QPushButton:hover {{ background: #059669; }}

        """)
        license_input_row.addWidget(self._license_activate_btn)
        license_layout.addLayout(license_input_row)
        license_btn_row = QHBoxLayout()
        license_btn_row.setSpacing(8)
        self._license_copy_fp_btn = QPushButton("📋 复制本机指纹")
        self._license_copy_fp_btn.setFixedHeight(30)
        self._license_copy_fp_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._license_copy_fp_btn.clicked.connect(self._copy_plugin_fingerprint)
        self._license_copy_fp_btn.setStyleSheet(f"""

            QPushButton {{ background: {THEME['hover']}; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 6px; padding: 2px 12px; font-size: 12px; }}

            QPushButton:hover {{ background: {THEME['accent']}33; }}

        """)
        license_btn_row.addWidget(self._license_copy_fp_btn)
        self._license_buy_btn = QPushButton("🛒 在线购买")
        self._license_buy_btn.setFixedHeight(30)
        self._license_buy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._license_buy_btn.clicked.connect(self._open_plugin_buy_page)
        self._license_buy_btn.setStyleSheet(f"""

            QPushButton {{ background: {THEME['accent2']}; color: #fff; border: none;

                border-radius: 6px; padding: 2px 12px; font-size: 12px; font-weight: bold; }}

            QPushButton:hover {{ background: {THEME['accent2']}dd; }}

        """)
        license_btn_row.addWidget(self._license_buy_btn)
        license_btn_row.addStretch()
        license_layout.addLayout(license_btn_row)
        self._license_group.setVisible(False)
        layout.addWidget(self._license_group)
        # 初始加载
        self._refresh_plugins()
    # =================== 能力清单 Tab ===================

    def _build_capabilities_tab(self):
        """构建能力清单 Tab — 展示盘古 AI 所有功能与能力"""
        import yaml
        from pathlib import Path
        layout = QVBoxLayout(self._cap_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        # 标题说明
        header = QHBoxLayout()
        title = QLabel("🧠 盘古 AI — 功能与能力清单")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        self._cap_count_label = QLabel("")
        self._cap_count_label.setStyleSheet(f"color: {THEME['accent']}; font-size: 13px; font-weight: bold;")
        header.addWidget(self._cap_count_label)
        layout.addLayout(header)
        subtitle = QLabel("以下列出盘古 AI 当前拥有的全部功能与能力，按类别分组。每次接到任务时，AI 会参考此清单选择最合适的工具。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        layout.addWidget(subtitle)
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""

            QScrollArea {{

                border: none;

                background: transparent;

            }}

            QScrollBar:vertical {{

                background: {THEME['bg_dark']};

                width: 8px;

                border-radius: 4px;

            }}

            QScrollBar::handle:vertical {{

                background: {THEME['border']};

                border-radius: 4px;

                min-height: 30px;

            }}

            QScrollBar::handle:vertical:hover {{

                background: {THEME['accent']};

            }}

        """)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(16)
        container_layout.setContentsMargins(0, 0, 0, 0)
        # 加载能力数据 — 优先从数据库读取，YAML 兜底
        caps = []
        summary = {}
        try:
            from src.database.db import get_capabilities_grouped, get_capability_summary
            caps = get_capabilities_grouped(active_only=True)
            summary = get_capability_summary()
        except Exception:
            # 数据库读取失败，回退到 YAML
            cap_path = Path(__file__).parent.parent.parent / "config" / "capabilities.yaml"
            try:
                with open(cap_path, 'r', encoding='utf-8') as f:
                    cap_data = yaml.safe_load(f)
                caps = cap_data.get('capabilities', [])
                summary = cap_data.get('summary', {})
            except Exception:
                pass
        total_items = 0
        for group in caps:
            cat = group.get('category', '')
            icon = group.get('icon', '📦')
            items = group.get('items', [])
            total_items += len(items)
            # 分类卡片
            card = QGroupBox(f"{icon}  {cat}")
            card.setStyleSheet(f"""

                QGroupBox {{

                    color: {THEME['accent']};

                    font-weight: bold;

                    font-size: 14px;

                    border: 1px solid {THEME['border']};

                    border-radius: 10px;

                    margin-top: 16px;

                    padding: 20px 16px 12px 16px;

                    background: {THEME['bg_card']};

                }}

                QGroupBox::title {{

                    subcontrol-origin: margin;

                    left: 16px;

                    padding: 0 10px;

                    background: {THEME['bg_card']};

                    border-radius: 4px;

                }}

            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            # 表头
            header_row = QHBoxLayout()
            h_name = QLabel("  能力名称")
            h_name.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;")
            h_name.setFixedWidth(180)
            h_desc = QLabel("功能描述")
            h_desc.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;")
            h_tool = QLabel("工具/来源")
            h_tool.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;")
            h_tool.setFixedWidth(260)
            header_row.addWidget(h_name)
            header_row.addWidget(h_desc, 1)
            header_row.addWidget(h_tool)
            card_layout.addLayout(header_row)
            # 分隔线
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"color: {THEME['border']};")
            card_layout.addWidget(sep)
            for item in items:
                row = QHBoxLayout()
                row.setSpacing(8)
                name = QLabel(f"  ◆ {item.get('name', '')}")
                name.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 13px;")
                name.setFixedWidth(180)
                desc = QLabel(item.get('desc', ''))
                desc.setWordWrap(True)
                desc.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
                tool = QLabel(item.get('tool', ''))
                tool.setStyleSheet(f"color: {THEME['accent2']}; font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;")
                tool.setFixedWidth(260)
                tool.setWordWrap(True)
                row.addWidget(name)
                row.addWidget(desc, 1)
                row.addWidget(tool)
                card_layout.addLayout(row)
            container_layout.addWidget(card)
        # 统计摘要
        if summary:
            summary_box = QGroupBox("📊 统计摘要")
            summary_box.setStyleSheet(f"""

                QGroupBox {{

                    color: {THEME['warning']};

                    font-weight: bold;

                    font-size: 14px;

                    border: 1px solid {THEME['border']};

                    border-radius: 10px;

                    margin-top: 16px;

                    padding: 20px 16px 12px 16px;

                    background: {THEME['bg_card']};

                }}

                QGroupBox::title {{

                    subcontrol-origin: margin;

                    left: 16px;

                    padding: 0 10px;

                    background: {THEME['bg_card']};

                    border-radius: 4px;

                }}

            """)
            s_layout = QFormLayout(summary_box)
            s_layout.setSpacing(8)
            s_layout.addRow(QLabel("能力分类:"), QLabel(f"{summary.get('total_categories', '?')} 个"))
            s_layout.addRow(QLabel("工具总数:"), QLabel(f"{summary.get('total_tools', '?')} 个"))
            s_layout.addRow(QLabel("本地工具:"), QLabel(", ".join(summary.get('local_tools', []))))
            s_layout.addRow(QLabel("云服务:"), QLabel(", ".join(summary.get('cloud_services', []))))
            for i in range(s_layout.rowCount()):
                label_item = s_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
                field_item = s_layout.itemAt(i, QFormLayout.ItemRole.FieldRole)
                if label_item and label_item.widget():
                    label_item.widget().setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 13px; font-weight: bold;")
                if field_item and field_item.widget():
                    field_item.widget().setStyleSheet(f"color: {THEME['text_primary']}; font-size: 13px;")
            container_layout.addWidget(summary_box)
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        # 更新计数
        self._cap_count_label.setText(f"共 {total_items} 项能力 · {len(caps)} 个分类")
    # =================== 环境与软件清单 Tab ===================

    def _build_installed_software_tab(self):
        """构建环境与软件清单 Tab — 展示电脑上已安装的开发环境/引擎/软件"""
        layout = QVBoxLayout(self._sw_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        # 标题行
        header = QHBoxLayout()
        title = QLabel("💻 环境、引擎与软件安装清单")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        self._sw_count_label = QLabel("")
        self._sw_count_label.setStyleSheet(f"color: {THEME['accent']}; font-size: 13px; font-weight: bold;")
        header.addWidget(self._sw_count_label)
        # 刷新按钮
        refresh_btn = QPushButton("🔄 重新扫描")
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self._refresh_software_list)
        refresh_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['bg_input']}; color: {THEME['accent']};

                border: 1px solid {THEME['border']}; border-radius: 6px;

                padding: 4px 16px; font-size: 12px;

            }}

            QPushButton:hover {{ border-color: {THEME['accent']}; background: {THEME['hover']}; }}

        """)
        header.addWidget(refresh_btn)
        layout.addLayout(header)
        subtitle = QLabel("以下列出电脑上已安装的关键开发环境、引擎和软件。AI 在执行任务前会参考此清单，避免重复安装已有工具。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        layout.addWidget(subtitle)
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""

            QScrollArea {{ border: none; background: transparent; }}

            QScrollBar:vertical {{ background: {THEME['bg_dark']}; width: 8px; border-radius: 4px; }}

            QScrollBar::handle:vertical {{ background: {THEME['border']}; border-radius: 4px; min-height: 30px; }}

            QScrollBar::handle:vertical:hover {{ background: {THEME['accent']}; }}

        """)
        container = QWidget()
        self._sw_container_layout = QVBoxLayout(container)
        self._sw_container_layout.setSpacing(16)
        self._sw_container_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        # 加载数据
        self._load_software_list()


    def _load_software_list(self):
        """从数据库加载软件清单并渲染"""
        # 清空
        while self._sw_container_layout.count() > 0:
            item = self._sw_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        try:
            from src.database.db import get_all_installed_software
            groups = get_all_installed_software(grouped=True)
        except Exception:
            groups = []
        total_items = 0
        for group in groups:
            cat = group.get('category', '')
            icon = group.get('icon', '📦')
            items = group.get('items', [])
            total_items += len(items)
            card = QGroupBox(f"{icon}  {cat}")
            card.setStyleSheet(f"""

                QGroupBox {{

                    color: {THEME['accent']}; font-weight: bold; font-size: 14px;

                    border: 1px solid {THEME['border']}; border-radius: 10px;

                    margin-top: 16px; padding: 20px 16px 12px 16px;

                    background: {THEME['bg_card']};

                }}

                QGroupBox::title {{

                    subcontrol-origin: margin; left: 16px; padding: 0 10px;

                    background: {THEME['bg_card']}; border-radius: 4px;

                }}

            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            # 表头
            hdr = QHBoxLayout()
            for w, t in [(180, "软件名称"), (100, "版本"), (280, "安装路径"), (70, "PATH"), (200, "备注")]:
                lbl = QLabel(f"  {t}")
                lbl.setFixedWidth(w)
                lbl.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;")
                hdr.addWidget(lbl)
            hdr.addStretch()
            card_layout.addLayout(hdr)
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"color: {THEME['border']};")
            card_layout.addWidget(sep)
            for item in items:
                row = QHBoxLayout()
                row.setSpacing(6)
                name_lbl = QLabel(f"  {'✅' if item.get('is_working') else '❌'} {item.get('name', '')}")
                name_lbl.setFixedWidth(180)
                name_lbl.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 13px;")
                ver_lbl = QLabel(item.get('version', '') or '—')
                ver_lbl.setFixedWidth(100)
                ver_lbl.setStyleSheet(f"color: {THEME['accent2']}; font-size: 12px; font-family: 'Consolas', monospace;")
                path_lbl = QLabel(item.get('install_path', '') or '—')
                path_lbl.setFixedWidth(280)
                path_lbl.setToolTip(item.get('install_path', ''))
                path_lbl.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 11px;")
                path_lbl.setWordWrap(False)
                path_status = "✅" if item.get('is_in_path') else "⚠️"
                path_lbl2 = QLabel(path_status)
                path_lbl2.setFixedWidth(70)
                path_lbl2.setToolTip("在PATH中" if item.get('is_in_path') else "不在PATH中，需用完整路径")
                path_lbl2.setStyleSheet(f"color: {'#22c55e' if item.get('is_in_path') else '#f59e0b'}; font-size: 14px;")
                note_lbl = QLabel(item.get('notes', '') or '')
                note_lbl.setFixedWidth(200)
                note_lbl.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 11px;")
                note_lbl.setWordWrap(True)
                row.addWidget(name_lbl)
                row.addWidget(ver_lbl)
                row.addWidget(path_lbl)
                row.addWidget(path_lbl2)
                row.addWidget(note_lbl)
                row.addStretch()
                card_layout.addLayout(row)
            self._sw_container_layout.addWidget(card)
        self._sw_container_layout.addStretch()
        self._sw_count_label.setText(f"共 {total_items} 款软件 · {len(groups)} 个分类")


    def _refresh_software_list(self):
        """重新扫描并刷新"""
        try:
            from src.database.db import scan_and_sync_installed_software
            scan_and_sync_installed_software()
            QMessageBox.information(self, "扫描完成", "已重新扫描系统软件并更新清单。")
        except Exception as e:
            QMessageBox.warning(self, "扫描失败", f"扫描过程出错: {e}")
        self._load_software_list()
    # =================== 记忆系统 Tab ===================

    def _build_memory_tab(self):
        """构建记忆系统 Tab — 展示 AI 持久化记忆数据"""
        layout = QVBoxLayout(self._memory_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        header = QHBoxLayout()
        title = QLabel("🧠 记忆系统")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        self._mem_count_label = QLabel("")
        self._mem_count_label.setStyleSheet(f"color: {THEME['accent']}; font-size: 13px; font-weight: bold;")
        header.addWidget(self._mem_count_label)
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self._load_memory_data)
        refresh_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['bg_input']}; color: {THEME['accent']};

                border: 1px solid {THEME['border']}; border-radius: 6px;

                padding: 4px 16px; font-size: 12px;

            }}

            QPushButton:hover {{ border-color: {THEME['accent']}; background: {THEME['hover']}; }}

        """)
        header.addWidget(refresh_btn)
        layout.addLayout(header)
        subtitle = QLabel("AI 会将重要信息持久化存储，重启后依然保留。分为游戏知识、技能经验、配置、通用四类。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        layout.addWidget(subtitle)
        # 搜索栏
        search_row = QHBoxLayout()
        self._mem_search = QLineEdit()
        self._mem_search.setPlaceholderText("搜索记忆内容...")
        self._mem_search.setStyleSheet(f"""

            QLineEdit {{

                background: {THEME['bg_input']}; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 6px;

                padding: 6px 12px; font-size: 13px;

            }}

            QLineEdit:focus {{ border-color: {THEME['accent']}; }}

        """)
        self._mem_search.textChanged.connect(self._filter_memory_data)
        search_row.addWidget(self._mem_search)
        self._mem_section_filter = QComboBox()
        self._mem_section_filter.addItems(["全部", "config", "games", "skills", "general"])
        self._mem_section_filter.currentTextChanged.connect(self._filter_memory_data)
        self._mem_section_filter.setStyleSheet(f"""

            QComboBox {{

                background: {THEME['bg_input']}; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 6px;

                padding: 6px 12px; font-size: 13px; min-width: 100px;

            }}

            QComboBox:focus {{ border-color: {THEME['accent']}; }}

            QComboBox::drop-down {{ border: none; }}

            QComboBox QAbstractItemView {{

                background: {THEME['bg_card']}; color: {THEME['text_primary']};

                selection-background-color: {THEME['accent']};

            }}

        """)
        search_row.addWidget(self._mem_section_filter)
        layout.addLayout(search_row)
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""

            QScrollArea {{ border: none; background: transparent; }}

            QScrollBar:vertical {{ background: {THEME['bg_dark']}; width: 8px; border-radius: 4px; }}

            QScrollBar::handle:vertical {{ background: {THEME['border']}; border-radius: 4px; min-height: 30px; }}

            QScrollBar::handle:vertical:hover {{ background: {THEME['accent']}; }}

        """)
        container = QWidget()
        self._mem_container_layout = QVBoxLayout(container)
        self._mem_container_layout.setSpacing(10)
        self._mem_container_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self._all_memories = []
        self._load_memory_data()


    def _load_memory_data(self):
        """从数据库加载记忆数据"""
        self._all_memories = []
        try:
            from src.database.db import get_all_memories
            db_memories = get_all_memories()
            self._all_memories = [
                {
                    "section": m["section"],
                    "key": m["key"],
                    "content": m["content"],
                    "importance": m.get("importance", "medium"),
                }
                for m in db_memories
            ]
        except Exception:
            pass
        self._render_memory_list(self._all_memories)


    def _filter_memory_data(self):
        """按搜索词和分类过滤记忆"""
        keyword = self._mem_search.text().lower()
        section = self._mem_section_filter.currentText()
        filtered = []
        for m in self._all_memories:
            if section != "全部" and m["section"] != section:
                continue
            if keyword and keyword not in m["key"].lower() and keyword not in m["content"].lower():
                continue
            filtered.append(m)
        self._render_memory_list(filtered)


    def _render_memory_list(self, memories):
        """渲染记忆列表"""
        while self._mem_container_layout.count() > 0:
            item = self._mem_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._mem_count_label.setText(f"共 {len(memories)} 条记忆")
        section_icons = {"config": "⚙️", "games": "🎮", "skills": "🔧", "general": "📋"}
        importance_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e", "unknown": THEME['text_muted']}
        for m in memories:
            card = QFrame()
            card.setStyleSheet(f"""

                QFrame {{

                    background: {THEME['bg_card']}; border: 1px solid {THEME['border']};

                    border-radius: 8px; padding: 12px;

                }}

            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            top_row = QHBoxLayout()
            icon = section_icons.get(m["section"], "📄")
            sec_label = QLabel(f"{icon} {m['section']}/{m['key']}")
            sec_label.setStyleSheet(f"color: {THEME['accent']}; font-weight: bold; font-size: 13px;")
            top_row.addWidget(sec_label)
            imp_label = QLabel(f"● {m['importance']}")
            imp_label.setStyleSheet(f"color: {importance_colors.get(m['importance'], THEME['text_muted'])}; font-size: 11px;")
            top_row.addWidget(imp_label)
            top_row.addStretch()
            del_btn = QPushButton("🗑 删除")
            del_btn.setFixedSize(60, 24)
            del_btn.setStyleSheet(f"""

                QPushButton {{

                    background: transparent; color: #ef4444; border: 1px solid #ef4444;

                    border-radius: 4px; font-size: 11px;

                }}

                QPushButton:hover {{ background: #ef4444; color: #fff; }}

            """)
            sec = m["section"]
            key = m["key"]
            del_btn.clicked.connect(lambda checked, s=sec, k=key: self._delete_memory(s, k))
            top_row.addWidget(del_btn)
            card_layout.addLayout(top_row)
            content_label = QLabel(m["content"][:500])
            content_label.setWordWrap(True)
            content_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
            card_layout.addWidget(content_label)
            self._mem_container_layout.addWidget(card)
        self._mem_container_layout.addStretch()


    def _delete_memory(self, section, key):
        """删除一条记忆（从数据库）"""
        reply = QMessageBox.question(self, "确认删除", f"确定要删除 {section}/{key} 吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from src.database.db import delete_memory
            if delete_memory(section, key):
                QMessageBox.information(self, "已删除", f"已删除记忆 {section}/{key}")
                self._load_memory_data()
            else:
                QMessageBox.warning(self, "未找到", f"未找到记忆 {section}/{key}")
        except Exception as e:
            QMessageBox.warning(self, "删除失败", str(e))
    # =================== 系统提示词 Tab ===================

    def _build_prompt_tab(self):
        """构建系统提示词 Tab — 查看当前 AI 系统提示词"""
        layout = QVBoxLayout(self._prompt_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        header = QHBoxLayout()
        title = QLabel("📝 系统提示词")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        self._prompt_info_label = QLabel("")
        self._prompt_info_label.setStyleSheet(f"color: {THEME['accent']}; font-size: 13px; font-weight: bold;")
        header.addWidget(self._prompt_info_label)
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self._load_prompt_data)
        refresh_btn.setStyleSheet(f"""

            QPushButton {{

                background: {THEME['bg_input']}; color: {THEME['accent']};

                border: 1px solid {THEME['border']}; border-radius: 6px;

                padding: 4px 16px; font-size: 12px;

            }}

            QPushButton:hover {{ border-color: {THEME['accent']}; background: {THEME['hover']}; }}

        """)
        header.addWidget(refresh_btn)
        layout.addLayout(header)
        subtitle = QLabel("以下为当前 AI 的系统提示词（只读）。提示词定义了 AI 的行为规则、能力边界和回答风格。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        layout.addWidget(subtitle)
        # 提示词来源标签
        self._prompt_source_label = QLabel("")
        self._prompt_source_label.setStyleSheet(f"color: {THEME['accent2']}; font-size: 12px; font-weight: bold;")
        layout.addWidget(self._prompt_source_label)
        # 文本显示区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""

            QScrollArea {{ border: 1px solid {THEME['border']}; border-radius: 8px; background: {THEME['bg_dark']}; }}

            QScrollBar:vertical {{ background: {THEME['bg_dark']}; width: 8px; border-radius: 4px; }}

            QScrollBar::handle:vertical {{ background: {THEME['border']}; border-radius: 4px; min-height: 30px; }}

            QScrollBar::handle:vertical:hover {{ background: {THEME['accent']}; }}

        """)
        self._prompt_text = QTextEdit()
        self._prompt_text.setReadOnly(True)
        self._prompt_text.setStyleSheet(f"""

            QTextEdit {{

                background: {THEME['bg_dark']}; color: {THEME['text_primary']};

                border: none; padding: 16px; font-size: 13px;

                font-family: 'Consolas', 'Microsoft YaHei', monospace;

            }}

        """)
        scroll.setWidget(self._prompt_text)
        layout.addWidget(scroll)
        self._load_prompt_data()


    def _load_prompt_data(self):
        """加载系统提示词（优先数据库，回退文件）"""
        prompt_text = ""
        source = ""
        # 优先从数据库读取
        try:
            from src.database.db import get_prompt_from_db
            db_prompt = get_prompt_from_db("system")
            if db_prompt:
                prompt_text = db_prompt["content"]
                updated = db_prompt.get("updated_at", "")
                reason = db_prompt.get("reason", "")
                source = f"💾 来源: 数据库 (更新: {updated}"
                if reason:
                    source += f", 原因: {reason}"
                source += ")"
        except Exception:
            pass
        # 回退：从文件读取
        if not prompt_text:
            custom_path = Path("data/prompts/system.txt")
            if custom_path.exists():
                prompt_text = custom_path.read_text(encoding="utf-8")
                source = "📂 来源: data/prompts/system.txt（自定义覆盖）"
            else:
                try:
                    from src.agent.prompts import DEFAULT_PROMPTS
                    prompt_text = DEFAULT_PROMPTS.get("system", "")
                    source = "📦 来源: 内置默认提示词"
                except Exception:
                    prompt_text = "无法加载提示词"
                    source = "⚠️ 加载失败"
        chars = len(prompt_text)
        lines = prompt_text.count('\n') + 1
        self._prompt_info_label.setText(f"{chars} 字符 · {lines} 行")
        self._prompt_source_label.setText(source)
        self._prompt_text.setPlainText(prompt_text)


    def _build_about_tab(self):
        """构建关于页 Tab — 显示 7Tan AI工具 简介与 LOGO"""
        layout = QVBoxLayout(self._about_tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        header = QHBoxLayout()
        title = QLabel("ℹ️ 关于 7Tan AI工具")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        # LOGO 显示
        logo_label = QLabel()
        logo_label.setFixedSize(128, 128)
        logo_label.setStyleSheet("border-radius: 16px; background: transparent;")
        base = Path(__file__).resolve().parents[2]
        for name in ("logo_v4_256.png", "logo_v4_512.png", "logo_v4_1024.png"):
            logo_path = base / "data" / "logo" / name
            if logo_path.exists():
                pix = QPixmap(str(logo_path)).scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pix)
                break
        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        # 标题与版本
        name_label = QLabel("7Tan AI工具")
        name_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        try:
            from src.config.version import APP_VERSION as _APP_VERSION
        except Exception:
            _APP_VERSION = "1.0.0"
        try:
            from src.config.build_info import BUILD_ID as _BUILD_ID
        except Exception:
            _BUILD_ID = "FREE"
        _ver_txt = f"v{_APP_VERSION}"
        if _BUILD_ID and not str(_BUILD_ID).startswith("FREE"):
            _ver_txt += f" · {_BUILD_ID}"
        version_label = QLabel(_ver_txt)
        version_label.setStyleSheet(f"font-size: 13px; color: {THEME['text_secondary']};")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        layout.addSpacing(10)
        # 简介文本
        intro_text = QTextEdit()
        intro_text.setReadOnly(True)
        intro_text.setStyleSheet(f"""

            QTextEdit {{

                background: {THEME['bg_dark']}; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 8px;

                padding: 20px; font-size: 13px;

                font-family: 'Microsoft YaHei', sans-serif;

            }}

        """)
        intro_text.setPlainText(
            "7Tan AI工具 是一款由 AI 驱动的个人创作与开发助手，代号「盘古」。\n"
            "它将软件研发、游戏内容生产、系统运维三大能力融为一体，\n"
            "让 AI 不只是聊天，而是真正替你干活。\n\n"
            "【核心能力】\n"
            "🤖 AI 智能中枢 — 接入 DeepSeek 等大模型，支持深度推理、\n"
            "   代码生成、文案创作与多轮对话\n\n"
            "🌐 游戏内容工厂 — 自动采集游戏资讯、撰写评测简介、\n"
            "   配图处理、敏感词审核，一键发布到网站\n\n"
            "💻 全栈开发助手 — 代码检索/审查/测试/重构、Git 版本管理、\n"
            "   Docker/K8s 运维、ADB 设备调试，200+ 工具随叫随到\n\n"
            "🧠 自我进化系统 — 可自主创建插件、优化提示词、管理记忆，\n"
            "   越用越聪明\n\n"
            "🎬 录屏与制图 — 屏幕录制、图像生成、语音合成\n\n"
            "【出品】老马"
        )
        layout.addWidget(intro_text)
        # ===== 软件更新 =====
        upd_row = QHBoxLayout()
        upd_row.addStretch()
        self._update_btn = QPushButton("🔄 检查更新")
        self._update_btn.setStyleSheet(f"background: {THEME['accent']}; color: #000; padding: 8px 28px;")
        self._update_btn.clicked.connect(self._check_update)
        upd_row.addWidget(self._update_btn)
        upd_row.addStretch()
        layout.addLayout(upd_row)
        self._update_status = QLabel("")
        self._update_status.setStyleSheet(f"font-size: 12px; color: {THEME['text_secondary']};")
        self._update_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._update_status)
        # ===== 用户协议 / 隐私政策 =====
        agree_row = QHBoxLayout()
        agree_row.addStretch()


        def _make_policy_btn(text: str, url: str):
            btn = QPushButton(text)
            btn.setStyleSheet(f"""

                QPushButton {{

                    background: transparent;

                    color: {THEME['text_secondary']};

                    border: none;

                    font-size: 12px;

                    text-decoration: underline;

                    padding: 4px 8px;

                }}

                QPushButton:hover {{ color: {THEME['accent']}; }}

            """)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(url)
            btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            return btn
        try:
            from src.config.loader import load_config as _load_cfg_policy
            _cfg_policy = _load_cfg_policy()
            _base_policy = _cfg_policy.get("site_7tan", {}).get("base_url", "")
            _site_root_policy = _base_policy.replace("/api", "") if _base_policy else "https://www.7tan.com"
            _site_root_policy = _site_root_policy.replace("img.7tan.cn", "www.7tan.com")
        except Exception:
            _site_root_policy = "https://www.7tan.com"
        agree_row.addWidget(_make_policy_btn("《用户协议》", _site_root_policy + "/agreement.php"))
        agree_row.addWidget(_make_policy_btn("《隐私政策》", _site_root_policy + "/privacy.php"))
        agree_row.addStretch()
        layout.addLayout(agree_row)
    # =================== 软件更新 ===================

    def _check_update(self):
        """手动检查更新（关于页按钮）"""
        self._update_status.setText("⏳ 正在检查更新…")
        self._update_btn.setEnabled(False)
        worker = ApiWorker("GET", f"{API_BASE}/api/update/check")


        def on_ok(data):
            self._update_btn.setEnabled(True)
            self._update_status.setText("")
            if data.get("error"):
                QMessageBox.warning(self, "检查更新", f"检查失败：{data['error']}")
                return
            if not data.get("has_update"):
                QMessageBox.information(
                    self, "检查更新", f"✅ 当前已是最新版本 v{data.get('current', '')}"
                )
                return
            info = dict(data.get("latest") or {})
            info["_current"] = data.get("current", "")
            dlg = UpdateDialog(info, parent=self)
            dlg.exec()


        def on_err(msg):
            self._update_btn.setEnabled(True)
            self._update_status.setText("")
            QMessageBox.warning(self, "检查更新", f"检查失败：{msg}")
        worker.finished.connect(on_ok)
        worker.error.connect(on_err)
        self._keep_worker(worker)
        worker.start()


    def _on_plugin_selected(self, row):
        """选中插件时显示详情"""
        if row < 0:
            return
        item = self._plugin_list.item(row)
        if not item:
            return
        info = item.data(Qt.ItemDataRole.UserRole + 1)  # 存储完整插件信息
        is_installed = item.data(Qt.ItemDataRole.UserRole + 2) or False
        detail = f"""<b>{info.get('icon', '')} {info.get('name', '')}</b>  v{info.get('version', '')}



📝 {info.get('description', '')}



👤 作者: {info.get('author', '')}

📂 分类: {info.get('category', '')}

🔧 工具: {', '.join(info.get('tools', []))}

📍 来源: {'🌐 在线仓库' if info.get('source') == 'remote' else '📦 本地内置'}



状态: {'✅ 已安装（重启后可用）' if is_installed else '⬇️ 未安装'}"""
        # ── 付费插件：授权状态醒目提示 ──
        if info.get('paid') or info.get('type') == 'paid':
            lic_html = self._plugin_license_status_html(info.get('id', ''))
            if lic_html:
                detail += f"\n\n🔑 授权状态: {lic_html}"
        if info.get('source') == 'remote' and not is_installed:
            detail += "\n\n💡 此插件来自在线仓库，点击安装将自动下载。"
        self._detail_label.setText(detail)
        self._install_btn.setEnabled(not is_installed)
        self._uninstall_btn.setEnabled(is_installed)
        self._update_license_panel()
    # =================== 付费插件授权管理 ===================

    def _plugin_license_status_html(self, plugin_id: str) -> str:
        """付费插件授权状态（HTML 彩色，供详情区显示）"""
        mod = self._plugin_license_module(plugin_id)
        if mod is None:
            return '<span style="color:#EF4444;font-weight:bold;">⚠️ 付费插件未安装，需先安装</span>'
        try:
            if mod.is_activated():
                return '<span style="color:#10B981;font-weight:bold;">✅ 已激活（永久授权，全部功能可用）</span>'
            left = mod.trial_left()
            if left > 0:
                return f'<span style="color:#F59E0B;font-weight:bold;">🔓 未激活 · 免费试用剩余 {left} 次</span>'
            return '<span style="color:#EF4444;font-weight:bold;">🚫 免费试用已用完，无法继续使用，请购买激活！</span>'
        except Exception:
            return ''

    def _plugin_license_module(self, plugin_id: str):
        """动态加载插件目录下的 license.py（无则返回 None）"""
        try:
            from src.plugins.manager import PLUGIN_DIR
            license_path = PLUGIN_DIR / plugin_id / "license.py"
            if not license_path.exists():
                return None
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"{plugin_id}_license_ui", license_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            return None


    def _current_license_plugin_id(self) -> str:
        """当前选中插件的 id（仅付费插件）"""
        row = self._plugin_list.currentRow()
        if row < 0:
            return ""
        item = self._plugin_list.item(row)
        if not item:
            return ""
        info = item.data(Qt.ItemDataRole.UserRole + 1) or {}
        if not (info.get("paid") or info.get("type") == "paid"):
            return ""
        return info.get("id", "")


    def _update_license_panel(self):
        """根据当前选中的插件刷新授权面板"""
        pid = self._current_license_plugin_id()
        if not pid:
            self._license_group.setVisible(False)
            return
        self._license_group.setVisible(True)
        self._license_input.clear()
        mod = self._plugin_license_module(pid)
        if mod is None:
            self._license_status_label.setText("⚠️ 该付费插件尚未安装，请先点击「📥 安装」后再激活。")
            self._license_activate_btn.setEnabled(False)
            return
        self._license_activate_btn.setEnabled(True)
        try:
            color = THEME['text_secondary']
            font_size = '12px'
            if mod.is_activated():
                text = "✅ 本插件已激活，永久授权，全部功能可用！"
                color = THEME['success']
                font_size = '13px'
            elif hasattr(mod, "status_text"):
                text = mod.status_text()
                try:
                    left = mod.trial_left()
                except Exception:
                    left = 1
                if left <= 0:
                    color = '#EF4444'
                    font_size = '13px'
                else:
                    color = '#F59E0B'
                    font_size = '13px'
            else:
                text = "🔑 输入授权码并点击「激活」解锁本插件。"
            self._license_status_label.setStyleSheet(
                f"color: {color}; font-size: {font_size}; font-weight: bold;")
            self._license_status_label.setText(text)
        except Exception as e:
            self._license_status_label.setStyleSheet(
                f"color: {THEME['text_secondary']}; font-size: 12px;")
            self._license_status_label.setText(f"⚠️ 读取授权状态失败: {e}")


    def _activate_plugin_license(self):
        """激活当前付费插件"""
        pid = self._current_license_plugin_id()
        key = self._license_input.text().strip()
        if not pid:
            return
        if not key:
            self._license_status_label.setText("⚠️ 请先粘贴授权码再点击激活。")
            return
        mod = self._plugin_license_module(pid)
        if mod is None:
            self._license_status_label.setText("⚠️ 授权模块不可用，请先安装插件。")
            return
        try:
            ok, msg = mod.activate(key)
            if ok:
                self._license_input.clear()
                self._license_status_label.setText("🎉 激活成功！" + (msg or "全部功能已解锁"))
            else:
                self._license_status_label.setText(msg or "❌ 激活失败")
        except Exception as e:
            self._license_status_label.setText(f"❌ 激活异常: {e}")


    def _copy_plugin_fingerprint(self):
        """复制本机指纹，供购买页面使用"""
        pid = self._current_license_plugin_id()
        mod = self._plugin_license_module(pid) if pid else None
        fp = ""
        if mod is not None and hasattr(mod, "get_fingerprint"):
            try:
                fp = mod.get_fingerprint()
            except Exception:
                fp = ""
        if not fp:
            try:
                from data.plugins.viral_writer import license as _vlic
                fp = _vlic.get_fingerprint()
            except Exception:
                fp = ""
        if fp:
            QApplication.clipboard().setText(fp)
            self._license_status_label.setText(f"📋 本机指纹已复制：{fp}\n购买时在插件中心粘贴此指纹，付款后即可获得授权码。")
        else:
            self._license_status_label.setText("⚠️ 获取本机指纹失败，请稍后重试。")


    def _open_plugin_buy_page(self):
        """打开在线购买页面"""
        QDesktopServices.openUrl(QUrl("https://www.7tan.com/pro.php"))
        self._license_status_label.setText("🛒 已打开在线购买页面（https://www.7tan.com/pro.php），登录后粘贴指纹即可购买。")


    def _refresh_plugins(self):
        """刷新本地插件列表"""
        from src.plugins import get_manager
        mgr = get_manager()
        results = mgr._search_local("")
        self._populate_plugin_list(results)


    def _populate_plugin_list(self, results: list):
        """用插件数据填充列表"""
        self._plugin_list.clear()
        installed_count = 0
        local_count = 0
        remote_count = 0
        for p in results:
            pid = p.get("id", "")
            name = p.get("name", pid)
            icon = p.get("icon", "📦")
            desc = p.get("description", "")[:40]
            ver = p.get("version", "")
            author = p.get("author", "未知")
            tools = p.get("tools", [])
            is_installed = p.get("installed", False)
            source = p.get("source", "local")
            if is_installed:
                installed_count += 1
                status = "✅"
            elif source == "remote":
                remote_count += 1
                status = "🌐"
            else:
                local_count += 1
                status = "⬇️"
            is_paid = p.get("paid") or p.get("type") == "paid"
            paid_flag = " 💰付费" if is_paid else ""
            lic_tag = ""
            lic_color = None
            if is_paid and is_installed:
                mod = self._plugin_license_module(pid)
                if mod is not None:
                    try:
                        if mod.is_activated():
                            lic_tag = " ✅已激活"
                        else:
                            left = int(mod.trial_left())
                            if left > 0:
                                lic_tag = f" 🔓试用剩{left}次"
                                lic_color = QColor("#F59E0B")
                            else:
                                lic_tag = " 🚫试用已用完·需购买激活"
                                lic_color = QColor("#EF4444")
                    except Exception:
                        lic_tag = ""
            item_text = f"{icon} {name}  v{ver}  [{status}]{paid_flag}{lic_tag}\n     {desc}\n     👤 {author} | 🔧 {', '.join(tools)}"
            item = QListWidgetItem(item_text)
            item.setSizeHint(QSize(0, 92))
            item.setData(Qt.ItemDataRole.UserRole, pid)
            item.setData(Qt.ItemDataRole.UserRole + 1, p)  # 存储完整信息
            item.setData(Qt.ItemDataRole.UserRole + 2, is_installed)
            if lic_color is not None:
                item.setForeground(lic_color)
            elif is_installed:
                item.setForeground(QColor(THEME['success']))
            elif source == "remote":
                item.setForeground(QColor(THEME['accent2']))
            self._plugin_list.addItem(item)
        total = len(results)
        self._plugin_status.setText(f"📊 共 {total} 个 | ✅ {installed_count} 已安装 | 📦 {local_count} 本地 | 🌐 {remote_count} 在线")
        self._detail_label.setText("选择一个插件查看详情")


    def _install_all_plugins(self):
        """一键安装全部插件"""
        from src.plugins import get_manager
        mgr = get_manager()
        manifest = mgr.get_manifest()
        installed = mgr.get_installed()
        ok_count = 0
        fail_count = 0
        for p in manifest:
            pid = p.get("id", "")
            if pid in installed:
                continue
            result = mgr.install(pid)
            if result.get("ok"):
                ok_count += 1
            else:
                fail_count += 1
        msg = f"安装完成: ✅ {ok_count} 个成功"
        if fail_count > 0:
            msg += f", ❌ {fail_count} 个失败"
        QMessageBox.information(self, "批量安装", msg)
        self._refresh_plugins()


    def _install_plugin(self):
        """安装选中插件"""
        item = self._plugin_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择要安装的插件")
            return
        plugin_id = item.data(Qt.ItemDataRole.UserRole)
        plugin_info = item.data(Qt.ItemDataRole.UserRole + 1) or {}
        from src.plugins import get_manager
        import json
        mgr = get_manager()
        # 如果是远程插件，先添加到本地清单
        if plugin_info.get("source") == "remote":
            manifest = mgr.get_manifest()
            local_ids = {p.get("id") for p in manifest}
            if plugin_id not in local_ids:
                manifest.append(plugin_info)
                from src.plugins.manager import MANIFEST_FILE
                MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = mgr.install(plugin_id)
        if result.get("ok"):
            QMessageBox.information(self, "安装成功", result.get("message", ""))
        else:
            QMessageBox.warning(self, "安装失败", result.get("error", ""))
        self._refresh_plugins()


    def _uninstall_plugin(self):
        """卸载选中插件"""
        item = self._plugin_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择要卸载的插件")
            return
        plugin_id = item.data(Qt.ItemDataRole.UserRole)
        from src.plugins import get_manager
        mgr = get_manager()
        installed = mgr.get_installed()
        if plugin_id not in installed:
            QMessageBox.information(self, "提示", "该插件未安装")
            return
        reply = QMessageBox.question(self, "确认卸载",
            f"确定要卸载插件 '{plugin_id}' 吗？\n工具代码会保留在 data/plugins/ 目录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            result = mgr.uninstall(plugin_id)
            QMessageBox.information(self, "卸载完成", result.get("message", ""))
            self._refresh_plugins()


    def _post_json(self, method, path, payload, ok_msg=None, err_msg=None):
        """通用保存方法"""
        worker = ApiWorker(method, f"{API_BASE}{path}", payload)
        if ok_msg:
            worker.finished.connect(lambda d, m=ok_msg: QMessageBox.information(self, "成功", m))
        if err_msg:
            worker.error.connect(lambda e, m=err_msg: QMessageBox.warning(self, "错误", f"{m}: {e}"))
        else:
            worker.error.connect(lambda e: QMessageBox.warning(self, "错误", f"保存失败: {e}"))
        worker.start()
        self._keep_worker(worker)
# ===== 主窗口 =====
# ============================================================
#  MainWindow - 主窗口
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        self._user_info = user_info or {}
        self.setWindowTitle("7Tan — AI工具")
        self.resize(1280, 820)
        self.setMinimumSize(960, 600)
        self._apply_window_icon()
        # 🎤 全局语音朗读桥：任何 Agent 回复（聊天/工作台任务）都可朗读，voice_mode 开关控制
        try:
            from src.agent.speak_bridge import init_global_tts
            init_global_tts()
        except Exception as e:
            print(f"[TTS-Bridge] 初始化失败: {e}")
        # 🎤 控制台朗读显式注册（模块级注册时序不可靠，这里兜底确保注册 + 日志可查）
        try:
            from src.ui.console_panel import init_console_tts
            init_console_tts()
            print("[TTS-Console] 控制台朗读初始化完成（app 启动显式注册）")
        except Exception as e:
            print(f"[TTS-Console] 初始化失败: {e}")
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
        self._status.setObjectName("status_bar_info")
        self._status.showMessage(f"🟢 就绪  |  {self._user_info.get('username', '未登录')}")
        self.setStatusBar(self._status)
        # 默认显示 AI 工作台
        self._sidebar.set_active("workspace")
        self._stack.setCurrentWidget(self._pages["workspace"])
        # 对话列表跟随 AI 工作台一起显示（与点击侧边栏行为一致）
        self._sidebar.session_sidebar.setVisible(True)
        # 🔄 启动后静默检查更新（延迟 8 秒，不阻塞启动）
        QTimer.singleShot(8000, self._auto_check_update)


    def _auto_check_update(self):
        """启动后后台静默检查更新，发现新版本弹出提示（可配置关闭）"""
        try:
            from src.core import updater as _updater
            if not _updater.auto_check_enabled():
                return
        except Exception:
            return


        def _on_ok(data):
            if not data or not data.get("has_update"):
                return
            info = dict(data.get("latest") or {})
            info["_current"] = data.get("current", "")
            dlg = UpdateDialog(info, parent=self)
            dlg.exec()


        def _on_err(msg):
            logger.debug(f"auto update check skipped: {msg}")
        worker = ApiWorker("GET", f"{API_BASE}/api/update/check")
        worker.finished.connect(_on_ok)
        worker.error.connect(_on_err)
        self._workers = getattr(self, "_workers", [])
        self._workers.append(worker)
        worker.start()


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
        if key == "market":
            # 插件市场 → 打开设置页并定位到插件市场 Tab（高亮保持「插件市场」）
            self._sidebar.set_active("market")
            self._stack.setCurrentWidget(self._pages["settings"])
            self._pages["settings"].show_plugin_tab()
            self._status.showMessage("🧩 插件市场")
            return
        if key in self._pages:
            self._stack.setCurrentWidget(self._pages[key])
            self._status.showMessage(f"📍 {key}")


    def _on_open_url(self, url: str):
        """侧边栏点击链接 → 切换到 AI 工作台并在浏览器打开"""
        self._sidebar.set_active("workspace")
        self._stack.setCurrentWidget(self._pages["workspace"])
        self._sidebar.session_sidebar.setVisible(True)
        self._status.showMessage(f"🌐 正在打开 {url}...")
        self._pages["workspace"].navigate_to_url(url)


    def _on_logout(self):
        """退出登录 → 关闭主窗口，重新弹出登录框"""
        self.close()
        launch_app()


    def showEvent(self, event):
        """主界面显示时：事件上报（带节流，不影响启动时的强制上报）"""
        try:
            from ..utils.user_stats import ping_analytics_async
            ping_analytics_async(force=False)
        except Exception:
            pass
        super().showEvent(event)


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
        # ===== 流量统计：关闭前上报（短超时，记录今日活跃） =====
        try:
            from ..utils.user_stats import ping_on_close
            ping_on_close()
        except Exception:
            pass
        super().closeEvent(event)
# ===== 启动入口 =====

def launch_app():
    """启动原生 PyQt6 桌面应用"""
    try:
        logger.info("📦 创建 QApplication...")
        # QWebEngine 必须在 QApplication 之前导入
        import PyQt6.QtWebEngineWidgets  # noqa: F401
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setStyleSheet(DARK_STYLESHEET)
        app.setApplicationName("7Tan")
        # ===== 浏览器 Cookie 持久化：重启保持登录态（固定存储路径 + 导出/恢复） =====
        try:
            from ..tools.cookie_manager import setup_cookie_persistence
            setup_cookie_persistence()
        except Exception as _ce:
            logger.warning(f"Cookie 持久化初始化失败: {_ce}")
        # ===== 主线程看门狗：UI 假死时自动 dump 线程栈到 logs/ =====
        try:
            from ..utils.watchdog import start as _wd_start, tick as _wd_tick
            _wd_start()
            _wd_timer = QTimer()
            _wd_timer.timeout.connect(_wd_tick)
            _wd_timer.start(1000)
            logger.info("🛡️ 主线程看门狗已启动（假死时自动 dump 栈）")
        except Exception as _wd_e:
            logger.warning(f"看门狗启动失败: {_wd_e}")
        # ===== 登录门卫（P2-8：核心逻辑已编译进 entry_auth.pyd，防 patch 跳过登录） =====
        from ..security.entry_auth import perform_login_gate
        user_info = perform_login_gate()
        if user_info is None:
            # 用户关闭登录窗口，退出应用
            logger.info("[Login] 用户取消登录，退出")
            return
        # ===== 新人引导：欢迎向导（API Key 设置，按用户独立判断） =====
        from .welcome_wizard import should_show_wizard, show_welcome_wizard
        _cur_username = (user_info or {}).get("username", "") or ""
        if should_show_wizard(_cur_username):
            logger.info(f"[Onboarding] 显示欢迎向导 (user={_cur_username or 'default'})...")
            api_key = show_welcome_wizard(username=_cur_username)
            if api_key:
                logger.info("[Onboarding] 用户已填写 API Key")
            # 向导关闭后处理待处理事件，防止主窗口显示"未响应"
            QApplication.processEvents()
        logger.info("🏗️ 创建主窗口...")
        window = MainWindow(user_info=user_info)
        window.show()
        # 立即处理绘制事件，防止白屏
        QApplication.processEvents()
        logger.info("🖥️ 原生 PyQt6 桌面应用已启动")
        # ===== 流量统计：后台线程发送 ping，绝不阻塞主线程 =====
        import threading as _thr

        def _bg_ping():
            try:
                from ..utils.user_stats import ping_analytics
                success = ping_analytics()
                logger.info(f"[Traffic] 统计 ping 结果: {'成功' if success else '失败'}")
            except Exception as _ping_err:
                logger.debug(f"[Traffic] ping 异常: {_ping_err}")
        _thr.Thread(target=_bg_ping, daemon=True, name="stats-ping").start()
        # ===== 新人引导：主界面交互式引导遮罩（延迟 500ms，确保窗口绘制完毕，按用户独立判断）=====
        from .onboarding import show_onboarding
        _ob_retry = {"count": 0}

        def _show_ob():
            try:
                # 主窗口尚未可见时延迟重试（最多 5 次），避免遮罩显示在未就绪的窗口上
                if not window.isVisible():
                    _ob_retry["count"] += 1
                    if _ob_retry["count"] <= 5:
                        logger.info(f"[Onboarding] 主窗口尚未可见，{_ob_retry['count']} 次延迟重试")
                        QTimer.singleShot(500, _show_ob)
                        return
                    logger.warning("[Onboarding] 主窗口长时间不可见，放弃显示引导遮罩")
                    return
                window._onboarding_overlay = show_onboarding(window, username=_cur_username)
            except Exception as _ob_err:
                logger.warning(f"[Onboarding] 引导遮罩异常: {_ob_err}")
        QTimer.singleShot(500, _show_ob)
        logger.info("[Onboarding] 主界面引导遮罩将在 500ms 后显示")
        app.exec()
        logger.info("👋 应用已关闭")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.exception(f"❌ 启动失败: {e}")
        # 弹窗显示错误，让用户能看到
        try:
            QMessageBox.critical(
                None, "7Tan 启动失败",
                f"主界面启动时遇到错误：\n\n{e}\n\n详细信息已写入日志文件。"
            )
        except Exception:
            pass
        raise
