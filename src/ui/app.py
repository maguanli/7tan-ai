"""
7坛AI小编 — 原生 PyQt6 桌面应用
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
    QFormLayout, QTabWidget, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QDialog, QDialogButtonBox,
    QPlainTextEdit, QStatusBar, QInputDialog,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QAction, QPixmap, QPainter,
    QBrush, QLinearGradient, QCursor, QFontDatabase,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QUrl, QObject,
    QPropertyAnimation, QEasingCurve, QRect,
)
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtCharts import (
    QChart, QChartView, QLineSeries, QBarSeries, QBarSet,
    QDateTimeAxis, QValueAxis, QPieSeries, QPieSlice, QBarCategoryAxis,
)

import requests
from loguru import logger

# ===== 颜色主题 =====
THEME = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_sidebar": "#0f0f23",
    "bg_input": "#1e1e3a",
    "accent": "#00d4ff",
    "accent2": "#7c3aed",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text_primary": "#e2e8f0",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border": "#1e293b",
    "hover": "#1e3a5f",
}

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
"""

# ===== API 基础 URL =====
API_BASE = "http://127.0.0.1:9800"


# ===== 后台请求线程 =====
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
                resp = requests.post(self._url, json=self._data, timeout=180)
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
class Sidebar(QFrame):
    page_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(200)
        self.setStyleSheet(f"background-color: {THEME['bg_sidebar']};")
        self._buttons = {}
        self._active_key = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("🎮 7坛AI小编")
        logo.setStyleSheet(f"color: {THEME['accent']}; font-size: 16px; font-weight: bold; padding: 8px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {THEME['border']};")
        layout.addWidget(line)
        layout.addSpacing(8)

        # 导航项
        nav_items = [
            ("dashboard", "📊", "仪表盘"),
            ("workspace", "🌐💬", "AI 工作台"),
            ("resources", "📦", "资源管理"),
            ("tasks", "⚙️", "任务监控"),
            ("sources", "🔗", "数据源"),
            ("analytics", "📈", "统计分析"),
            ("settings", "🔧", "设置"),
        ]

        for key, icon, label in nav_items:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setProperty("flat", "true")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # 底部信息
        version = QLabel("v5.1.0")
        version.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 10px; padding: 8px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

    def _on_click(self, key):
        self.set_active(key)
        self.page_changed.emit(key)

    def set_active(self, key):
        for k, btn in self._buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._active_key = key


# ===== 仪表盘页面 =====
class DashboardPage(QWidget):
    def __init__(self):
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

        # 定时刷新
        self._timer = QTimer()
        self._timer.timeout.connect(self.refresh)
        self._timer.start(10000)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

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


# ===== Enter 发送输入框 =====
class _EnterToSendEdit(QPlainTextEdit):
    send_triggered = pyqtSignal()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            modifiers = event.modifiers()
            if (modifiers & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)):
                # Shift/Ctrl+Enter = 换行
                super().keyPressEvent(event)
            else:
                self.send_triggered.emit()
        else:
            super().keyPressEvent(event)


# ===== AI 对话页面 =====
class ChatPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("💬 AI 对话")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)

        # 会话管理
        toolbar = QHBoxLayout()
        self._session_combo = QComboBox()
        self._session_combo.setMinimumWidth(200)
        self._session_combo.addItem("新建对话")
        toolbar.addWidget(self._session_combo)

        new_btn = QPushButton("+ 新对话")
        new_btn.setFixedWidth(100)
        new_btn.clicked.connect(self._new_session)
        toolbar.addWidget(new_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 聊天消息区
        self._chat_area = QScrollArea()
        self._chat_area.setWidgetResizable(True)
        self._chat_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 10px;
            }}
        """)

        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._messages_layout.setSpacing(8)
        self._messages_layout.addStretch()
        self._chat_area.setWidget(self._messages_container)
        layout.addWidget(self._chat_area, 1)

        # 输入区
        input_layout = QHBoxLayout()
        self._input = _EnterToSendEdit()
        self._input.setPlaceholderText("输入消息... (Enter 发送, Shift+Enter 换行)")
        self._input.setMaximumHeight(100)
        self._input.setMinimumHeight(48)
        self._input.send_triggered.connect(self._send_message)
        input_layout.addWidget(self._input, 1)

        send_btn = QPushButton("发送 ▶")
        send_btn.setFixedWidth(100)
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

        # 快捷提示
        hints_layout = QHBoxLayout()
        hints = ["帮我找个新游戏", "检查最新资源", "发布待处理资源", "查看统计数据"]
        for hint in hints:
            h_btn = QPushButton(hint)
            h_btn.setProperty("flat", "true")
            h_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            h_btn.clicked.connect(lambda checked, h=hint: self._use_hint(h))
            hints_layout.addWidget(h_btn)
        hints_layout.addStretch()
        layout.addLayout(hints_layout)

        self._current_session_id = None
        self._sessions_loaded = False
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)

    def _use_hint(self, text):
        self._input.setPlainText(text)
        self._send_message()

    def _new_session(self):
        self._current_session_id = None
        # 清空消息
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add_message("system", "新对话已开始，输入指令开始操作吧 👋")

    def _keep_worker(self, worker):
        """保持 worker 引用防止 GC — 完成后自动清理"""
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.finished.connect(lambda d, w=worker: self._workers.remove(w) if w in self._workers else None)
        worker.error.connect(lambda e, w=worker: self._workers.remove(w) if w in self._workers else None)

    def _send_message(self):
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._add_message("user", text)
        self._input.clear()

        # 发送请求
        data = {"message": text}
        if self._current_session_id:
            data["session_id"] = self._current_session_id

        self._worker = ApiWorker("POST", f"{API_BASE}/api/chat/send", data)
        self._worker.finished.connect(self._on_response)
        self._worker.error.connect(lambda e: self._add_message("error", f"❌ 请求失败: {e}"))
        self._worker.start()
        self._keep_worker(self._worker)

        self._add_message("system", "⏳ AI 正在处理...")

    def _on_response(self, data):
        # 移除等待消息
        if self._messages_layout.count() > 2:
            item = self._messages_layout.itemAt(self._messages_layout.count() - 2)
            if item.widget():
                w = item.widget()
                if hasattr(w, 'property') and w.property("role") == "system":
                    w.deleteLater()

        self._current_session_id = data.get("session_id", self._current_session_id)
        result = data.get("result", "无响应")
        cost = data.get("cost", 0)
        iterations = data.get("iterations", 0)
        success = data.get("success", False)

        prefix = "✅" if success else "❌"
        footer = f"\n\n---\n💰 ¥{cost:.4f} | 🔄 {iterations} 次迭代"
        self._add_message("assistant", f"{prefix} {result}{footer}")

    def _add_message(self, role, text):
        msg = QFrame()
        msg.setProperty("role", role)

        if role == "user":
            msg.setStyleSheet(f"""
                QFrame {{
                    background-color: {THEME['accent']};
                    color: #000;
                    border-radius: 10px;
                    padding: 10px 14px;
                    margin: 4px 0 4px 60px;
                }}
            """)
        elif role == "assistant":
            msg.setStyleSheet(f"""
                QFrame {{
                    background-color: {THEME['bg_input']};
                    color: {THEME['text_primary']};
                    border-radius: 10px;
                    padding: 10px 14px;
                    margin: 4px 60px 4px 0;
                }}
            """)
        elif role == "error":
            msg.setStyleSheet(f"""
                QFrame {{
                    background-color: {THEME['danger']}22;
                    color: {THEME['danger']};
                    border: 1px solid {THEME['danger']};
                    border-radius: 10px;
                    padding: 10px 14px;
                }}
            """)
        else:
            msg.setStyleSheet(f"""
                QFrame {{
                    color: {THEME['text_muted']};
                    padding: 4px 14px;
                    font-style: italic;
                }}
            """)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label_layout = QVBoxLayout(msg)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.addWidget(label)

        # 插入到 stretch 之前
        idx = self._messages_layout.count() - 1
        self._messages_layout.insertWidget(idx, msg)

        # 滚动到底部
        QTimer.singleShot(50, lambda: self._chat_area.verticalScrollBar().setValue(
            self._chat_area.verticalScrollBar().maximum()
        ))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._sessions_loaded:
            self._sessions_loaded = True
            self._load_sessions()

    def _load_sessions(self):
        self._worker = ApiWorker("GET", f"{API_BASE}/api/chat/history")
        self._worker.finished.connect(self._on_sessions_loaded)
        self._worker.error.connect(lambda e: logger.error(f"加载会话列表失败: {e}"))
        self._worker.start()
        self._keep_worker(self._worker)

    def _on_sessions_loaded(self, data):
        sessions = data.get("sessions", [])
        self._session_combo.blockSignals(True)
        self._session_combo.clear()
        self._session_combo.addItem("新建对话")
        for s in sessions:
            sid = s.get("id", "")
            title = s.get("title", sid)[:40] or sid[:20]
            self._session_combo.addItem(f"  {title}", sid)
        self._session_combo.blockSignals(False)

    def _on_session_changed(self, index):
        if index <= 0:
            return
        session_id = self._session_combo.itemData(index)
        if session_id:
            self._load_history(session_id)

    def _load_history(self, session_id):
        self._current_session_id = session_id
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add_message("system", "⏳ 加载对话历史...")
        self._worker = ApiWorker("GET", f"{API_BASE}/api/chat/history?session_id={session_id}")
        self._worker.finished.connect(self._on_history_loaded)
        self._worker.start()
        self._keep_worker(self._worker)

    def _on_history_loaded(self, data):
        if self._messages_layout.count() > 1:
            item = self._messages_layout.itemAt(self._messages_layout.count() - 2)
            if item.widget():
                w = item.widget()
                if hasattr(w, 'property') and w.property("role") == "system":
                    w.deleteLater()
        messages = data.get("messages", [])
        for msg in messages:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            self._add_message(role, content)


# ===== 资源管理页面（表格） =====
class ResourceTablePage(QWidget):
    def __init__(self):
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
        bottom.addStretch()
        self._count_label = QLabel("共 0 条")
        self._count_label.setStyleSheet(f"color: {THEME['text_muted']};")
        bottom.addWidget(self._count_label)
        layout.addLayout(bottom)

        self._timer = QTimer()
        self._timer.timeout.connect(self.refresh)
        self._timer.start(30000)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

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


# ===== 任务监控页面 =====
class TasksPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("⚙️ 任务监控")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)

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
        self._timer.start(5000)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        self._worker = ApiWorker("GET", f"{API_BASE}/api/tasks")
        self._worker.finished.connect(self._on_data)
        self._worker.error.connect(lambda e: logger.error(f"任务加载失败: {e}"))
        self._worker.start()

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


# ===== 数据源管理页面 =====
class SourcesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("🌐 数据源管理")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {THEME['text_primary']};")
        layout.addWidget(title)

        add_btn = QPushButton("+ 添加源站")
        add_btn.clicked.connect(self._add_source)
        add_btn.setFixedWidth(120)
        layout.addWidget(add_btn)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["名称", "URL", "类型", "需登录", "状态", "上次爬取"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
            self._table.setItem(i, 0, QTableWidgetItem(s.get("name", "")))
            self._table.setItem(i, 1, QTableWidgetItem(s.get("url", "")))
            self._table.setItem(i, 2, QTableWidgetItem(s.get("site_type", "")))
            self._table.setItem(i, 3, QTableWidgetItem("是" if s.get("need_login") else "否"))
            enabled = s.get("enabled", True)
            status_item = QTableWidgetItem("启用" if enabled else "禁用")
            status_item.setForeground(QColor(THEME["success"] if enabled else THEME["danger"]))
            self._table.setItem(i, 4, status_item)
            self._table.setItem(i, 5, QTableWidgetItem(str(s.get("last_crawl_at", "—"))))

    def _add_source(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加源站")
        dialog.setMinimumWidth(400)
        dialog_layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        url_edit = QLineEdit()
        type_combo = QComboBox()
        type_combo.addItems(["game", "software", "other"])
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



# ===== 独立浏览器窗口 =====
class DetachedBrowserWindow(QMainWindow):
    """弹出式独立浏览器窗口 — 带工具栏和关闭按钮"""

    def __init__(self, url: str = "about:blank", title: str = "独立窗口"):
        super().__init__()
        self.setWindowTitle(f"🌐 {title}")
        self.resize(1024, 700)
        self.setMinimumSize(400, 300)

        from PyQt6.QtWebEngineWidgets import QWebEngineView

        # ===== 顶部工具栏 =====
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet(f"""
            QToolBar {{
                background: {THEME['bg_dark']};
                border-bottom: 1px solid {THEME['border']};
                padding: 4px 8px;
                spacing: 6px;
            }}
        """)

        # 后退
        back_btn = QPushButton("⬅")
        back_btn.setFixedSize(32, 28)
        back_btn.setToolTip("后退")
        back_btn.setStyleSheet(f"QPushButton {{ background:{THEME['bg_input']}; color:{THEME['text_secondary']}; border:1px solid {THEME['border']}; border-radius:6px; font-size:14px; }} QPushButton:hover {{ background:{THEME['accent']}; color:#000; }}")
        toolbar.addWidget(back_btn)

        # 前进
        fwd_btn = QPushButton("➡")
        fwd_btn.setFixedSize(32, 28)
        fwd_btn.setToolTip("前进")
        fwd_btn.setStyleSheet(f"QPushButton {{ background:{THEME['bg_input']}; color:{THEME['text_secondary']}; border:1px solid {THEME['border']}; border-radius:6px; font-size:14px; }} QPushButton:hover {{ background:{THEME['accent']}; color:#000; }}")
        toolbar.addWidget(fwd_btn)

        # 刷新
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(32, 28)
        refresh_btn.setToolTip("刷新")
        refresh_btn.setStyleSheet(f"QPushButton {{ background:{THEME['bg_input']}; color:{THEME['text_secondary']}; border:1px solid {THEME['border']}; border-radius:6px; font-size:14px; }} QPushButton:hover {{ background:{THEME['accent']}; color:#000; }}")
        toolbar.addWidget(refresh_btn)

        # URL 输入框
        self._win_url = QLineEdit()
        self._win_url.setPlaceholderText("输入网址，按回车打开…")
        self._win_url.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME['bg_input']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
        """)
        toolbar.addWidget(self._win_url)

        # 右侧弹簧 + 关闭按钮
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 28)
        close_btn.setToolTip("关闭窗口 (Ctrl+W)")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {THEME['danger']};
                color: white;
                border-color: {THEME['danger']};
            }}
        """)
        close_btn.clicked.connect(self.close)
        toolbar.addWidget(close_btn)

        self.addToolBar(toolbar)

        # ===== 浏览器视图 =====
        self._view = QWebEngineView()
        self._view.setStyleSheet("background-color: white;")
        self._view.urlChanged.connect(lambda u: self.setWindowTitle(f"🌐 {u.toString()[:60]}"))
        self._view.titleChanged.connect(lambda t: self.setWindowTitle(f"🌐 {t}"))
        self._view.urlChanged.connect(lambda u: self._win_url.setText(u.toString()))
        self._view.loadStarted.connect(lambda: self._win_url.setStyleSheet(
            self._win_url.styleSheet().replace("1px solid " + THEME['border'],
                                                "1px solid " + THEME['accent'])
        ))
        self._view.loadFinished.connect(lambda ok: self._win_url.setStyleSheet(
            self._win_url.styleSheet().replace("1px solid " + THEME['accent'],
                                                "1px solid " + THEME['border'])
        ))
        self.setCentralWidget(self._view)

        # 工具栏按钮绑定
        back_btn.clicked.connect(self._view.back)
        fwd_btn.clicked.connect(self._view.forward)
        refresh_btn.clicked.connect(self._view.reload)
        self._win_url.returnPressed.connect(lambda: self._view.load(QUrl(self._win_url.text())))

        # 快捷键
        from PyQt6.QtGui import QShortcut, QKeySequence
        close_sc = QShortcut(QKeySequence("Ctrl+W"), self)
        close_sc.activated.connect(self.close)
        focus_url_sc = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_url_sc.activated.connect(lambda: self._win_url.setFocus())

        # 注册到 browser_tools
        import src.tools.browser_tools as bt
        bt.register_web_view(self._view)

        if url and url != "about:blank":
            self._view.load(QUrl(url))
        else:
            self._view.setHtml("<h2 style='color:#aaa;text-align:center;margin-top:100px'>🌐 新窗口 — 输入网址开始浏览</h2>")

    @property
    def view(self):
        return self._view


# ===== 浏览器页面 =====
class BrowserPage(QWidget):
    """内置浏览器 — 多标签页，使用 PyQt6 QWebEngineView 原生渲染网页"""

    def __init__(self):
        super().__init__()
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile

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
        self._back_btn.setStyleSheet(f"QPushButton {{ font-size:14px; padding:4px; }}")
        url_layout.addWidget(self._back_btn)

        self._forward_btn = QPushButton("➡")
        self._forward_btn.setToolTip("前进")
        self._forward_btn.setFixedWidth(36)
        self._forward_btn.clicked.connect(self._forward_current)
        self._forward_btn.setEnabled(False)
        self._forward_btn.setStyleSheet(f"QPushButton {{ font-size:14px; padding:4px; }}")
        url_layout.addWidget(self._forward_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("刷新")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._refresh_current)
        refresh_btn.setStyleSheet(f"QPushButton {{ font-size:14px; padding:4px; }}")
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

        # 🔲 独立窗口按钮
        detach_btn = QPushButton("🔲")
        detach_btn.setToolTip("将当前标签页弹出为独立窗口")
        detach_btn.setFixedWidth(36)
        detach_btn.clicked.connect(self._detach_current_tab)
        detach_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_input']};
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                font-size: 14px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background: {THEME['accent']};
                color: #000;
            }}
        """)
        url_layout.addWidget(detach_btn)

        # 🪟 新窗口按钮
        new_win_btn = QPushButton("🪟")
        new_win_btn.setToolTip("打开新浏览器窗口 (Ctrl+N)")
        new_win_btn.setFixedWidth(36)
        new_win_btn.clicked.connect(self._open_new_window)
        new_win_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_input']};
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                font-size: 14px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background: {THEME['accent2']};
                color: #fff;
            }}
        """)
        url_layout.addWidget(new_win_btn)
        layout.addLayout(url_layout)

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
                background: {THEME['bg_card']};
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
                image: none;
                background: transparent;
            }}
            QTabBar::close-button:hover {{
                background: {THEME['danger']}66;
                border-radius: 4px;
            }}
        """)

        # "+" 新标签按钮 — 放在 tab bar 右侧
        self._new_tab_btn = QPushButton("＋")
        self._new_tab_btn.setFixedSize(32, 32)
        self._new_tab_btn.setToolTip("新建标签页 (Ctrl+T)")
        self._new_tab_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['accent']};
                color: #000;
                border: none;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {THEME['accent']}dd;
            }}
        """)
        self._new_tab_btn.clicked.connect(self._add_tab)
        self._tab_widget.setCornerWidget(self._new_tab_btn, Qt.Corner.TopRightCorner)

        layout.addWidget(self._tab_widget, 1)

        # 状态栏
        self._status = QLabel("🟢 就绪 | Ctrl+T 新标签 | Ctrl+W 关标签 | Ctrl+N 新窗口 | 输入网址按回车打开")
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

        close_tab_sc = QShortcut(QKeySequence("Ctrl+W"), self)
        close_tab_sc.activated.connect(self._close_current_tab)
        close_tab_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        new_win_sc = QShortcut(QKeySequence("Ctrl+N"), self)
        new_win_sc.activated.connect(self._open_new_window)
        new_win_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        focus_url_sc = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_url_sc.activated.connect(lambda: self._url_input.setFocus())
        focus_url_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

    # ===== 键盘快捷键辅助方法 =====

    def _close_current_tab(self):
        """关闭当前标签页（Ctrl+W）"""
        idx = self._tab_widget.currentIndex()
        if idx >= 0 and len(self._tabs) > 1:
            self._close_tab(idx)

    # ===== 新窗口 =====

    def _open_new_window(self):
        """打开一个新的独立浏览器窗口 (Ctrl+N)"""
        win = DetachedBrowserWindow(url="about:blank", title="新窗口")
        # 保存引用防止 GC
        if not hasattr(self, '_detached_windows'):
            self._detached_windows = []
        self._detached_windows.append(win)
        win.show()

    # ===== 标签页管理 =====

    def _create_web_view(self):
        """创建一个配置好的 QWebEngineView"""
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        view = QWebEngineView()
        view.setStyleSheet("background-color: white; border-radius: 0;")

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

        # 立即设为当前 view（不等 currentChanged 信号，避免初始化时未触发）
        self._current_view = view
        if url == "about:blank":
            self._url_input.setText("")
        else:
            self._url_input.setText(url)
        self._back_btn.setEnabled(False)
        self._forward_btn.setEnabled(False)

        # 注册到 browser_tools
        import src.tools.browser_tools as bt
        bt.register_web_view(view)

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
            view.loadStarted.disconnect()
            view.loadFinished.disconnect()
        except Exception:
            pass

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
            return  # 至少保留一个标签页

        idx = self._tab_widget.currentIndex()
        if idx < 0:
            return

        tab = self._tabs[idx]
        view = tab["view"]
        url = tab.get("url", "about:blank")
        title = tab.get("title", "独立窗口")

        # 断开主窗口的信号
        try:
            view.urlChanged.disconnect()
            view.titleChanged.disconnect()
            view.loadStarted.disconnect()
            view.loadFinished.disconnect()
        except Exception:
            pass

        # 从标签栏移除
        self._tab_widget.removeTab(idx)
        self._tabs.pop(idx)
        self._update_tab_visibility()

        # 如果当前 view 就是被移除的，切换 current
        if view is self._current_view:
            new_idx = self._tab_widget.currentIndex()
            if new_idx >= 0 and new_idx < len(self._tabs):
                self._current_view = self._tabs[new_idx]["view"]
                self._on_tab_changed(new_idx)
            else:
                self._current_view = None

        # 创建独立窗口
        win = DetachedBrowserWindow(url=url, title=title)
        old_view = win.centralWidget()
        win.takeCentralWidget()
        if old_view:
            old_view.deleteLater()
        win.setCentralWidget(view)
        win.setWindowTitle(f"🌐 {title}")
        if url and url != "about:blank":
            view.load(QUrl(url))
        win.show()

        # 跟踪窗口防止 GC
        if not hasattr(self, '_detached_windows'):
            self._detached_windows = []
        self._detached_windows.append(win)

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
        import src.tools.browser_tools as bt
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

        # 如果没有当前 view，尝试从第一个标签获取或创建新标签
        if self._current_view is None:
            if self._tabs:
                self._current_view = self._tabs[0]["view"]
                self._tab_widget.setCurrentIndex(0)
            else:
                self._add_tab(url=url, title="新标签页")
                return

        # 更新当前标签的 url 追踪
        for tab in self._tabs:
            if tab["view"] is self._current_view:
                tab["url"] = url
                break

        self._status.setText(f"⏳ 正在加载 {url}…")
        self._current_view.load(QUrl(url))

    def _refresh_current(self):
        if self._current_view:
            self._current_view.reload()

    def _back_current(self):
        if self._current_view:
            self._current_view.back()

    def _forward_current(self):
        if self._current_view:
            self._current_view.forward()


# ===== AI 工作台（浏览器 + 对话 左右分屏） =====
class ChatBrowserSplitPage(QWidget):
    """浏览器在左、AI 对话在右，中间可拖动分隔条"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

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

        # 浏览器（左）自动通过 register_web_view 注册到全局 BrowserBridge
        self.browser = BrowserPage()
        self.chat = ChatPage()

        splitter.addWidget(self.browser)
        splitter.addWidget(self.chat)
        splitter.setSizes([560, 680])  # 默认 560:680 分割
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)


# ===== 统计分析页面 =====
class AnalyticsPage(QWidget):
    def __init__(self):
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
class SettingsPage(QWidget):
    def __init__(self):
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

        # 三个 Tab
        self._ai_tab = QWidget()
        self._site_tab = QWidget()
        self._oss_tab = QWidget()
        self._build_ai_tab()
        self._build_site_tab()
        self._build_oss_tab()

        self._tabs.addTab(self._ai_tab, "🤖 AI 模型")
        self._tabs.addTab(self._site_tab, "🌐 站点设置")
        self._tabs.addTab(self._oss_tab, "☁️ OSS 存储")
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
            self._load_settings()

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

        def _make_icon_btn(text, tooltip, bg_color, hover_color):
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setFixedSize(36, 36)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {bg_color}; color: white; border-radius: 18px; font-size: 14px; border: none; }}
                QPushButton:hover {{ background: {hover_color}; }}
            """)
            return btn

        add_btn = _make_icon_btn("＋", "新建模型配置", THEME['success'], "#059669")
        add_btn.clicked.connect(self._add_config)
        btn_row.addWidget(add_btn)

        del_btn = _make_icon_btn("✕", "删除选中配置", THEME['danger'], "#dc2626")
        del_btn.clicked.connect(self._delete_config)
        btn_row.addWidget(del_btn)

        active_btn = _make_icon_btn("⭐", "设为当前使用的模型", THEME['warning'], "#d97706")
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
        self._ai_model.addItems(["deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner", "gpt-4o", "gpt-4o-mini", "qwen-max", "glm-4-plus"])
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
        self._site_url.setPlaceholderText("https://img.7tan.cn")
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

        form.addRow("Bucket:", self._oss_bucket)
        form.addRow("Endpoint:", self._oss_endpoint)
        form.addRow("AccessKey:", self._oss_key)
        form.addRow("SecretKey:", self._oss_secret)
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
        """切换 API Key 显示/隐藏 — 显示时从本地配置加载真实密钥"""
        if checked:
            # 从本地配置文件获取真实密钥（绕过脱敏）
            from src.config.loader import load_config
            config = load_config()
            key_name = self._config_list.currentItem().data(Qt.ItemDataRole.UserRole)
            real_key = config.get("ai", {}).get("configs", {}).get(key_name, {}).get("api_key", "")
            if real_key:
                self._ai_key.setText(real_key)
            self._ai_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self._ai_key_toggle.setText("隐藏")
        else:
            # 恢复脱敏显示
            item = self._config_list.currentItem()
            if item:
                cfg = self._ai_configs.get(item.data(Qt.ItemDataRole.UserRole), {})
                self._ai_key.setText(cfg.get("api_key", ""))
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
            self._ai_configs = {"deepseek": {"provider": "deepseek", "model": "deepseek-chat", "base_url": "https://api.deepseek.com/v1", "api_key": ""}}
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
            self._ai_configs = {"deepseek": {"provider": "deepseek", "model": "deepseek-chat", "base_url": "https://api.deepseek.com/v1", "api_key": ""}}
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

        site = settings.get("site_7tan", {})
        self._site_url.setText(site.get("base_url", ""))
        self._site_user.setText(site.get("username", ""))
        self._publish_interval.setValue(site.get("publish_delay_min", 30))
        # 重置密码显示/隐藏按钮状态
        self._site_pass_toggle.setChecked(False)
        self._site_pass.setEchoMode(QLineEdit.EchoMode.Password)

        oss = settings.get("oss", {})
        self._oss_bucket.setText(oss.get("bucket", ""))
        self._oss_endpoint.setText(oss.get("endpoint", oss.get("region", "")))
        self._oss_key.setText(oss.get("access_key", ""))
        self._oss_secret.setText(oss.get("secret_key", ""))

    def _save_ai_config(self):
        """只保存当前编辑的 AI 模型配置（不发送其他配置，防止跨配置污染）"""
        item = self._config_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个配置。")
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        self._ai_configs[key] = {
            "provider": self._ai_provider.currentText(),
            "model": self._ai_model.currentText(),
            "base_url": self._ai_base.text(),
            "api_key": self._ai_key.text() if self._ai_key.text() and self._ai_key.text() != "••••••••"
                      else self._ai_configs.get(key, {}).get("api_key", ""),
        }
        # 只发送当前编辑的配置，避免其他模型的配置被覆盖
        payload = {
            "ai": {
                "active": self._active_config,
                "configs": {key: self._ai_configs[key]},
            }
        }
        self._post_json("PUT", "/api/settings", payload, ok_msg=f"模型「{key}」已保存！")

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
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("7tanAI — AI 自动更新系统")
        self.resize(1280, 820)
        self.setMinimumSize(960, 600)

        # 中心 widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._switch_page)
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

        # 状态栏
        self._status = QStatusBar()
        self._status.showMessage("🟢 就绪")
        self.setStatusBar(self._status)

        # 默认显示仪表盘
        self._sidebar.set_active("dashboard")
        self._stack.setCurrentWidget(self._pages["dashboard"])

    def _switch_page(self, key):
        if key in self._pages:
            self._stack.setCurrentWidget(self._pages[key])
            self._status.showMessage(f"📍 {key}")


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
        app.setApplicationName("7tanAI")

        logger.info("🏗️ 创建主窗口...")
        window = MainWindow()
        window.show()
        logger.info("🖥️ 原生 PyQt6 桌面应用已启动")
        app.exec()
        logger.info("👋 应用已关闭")
    except Exception as e:
        logger.exception(f"❌ 启动失败: {e}")
        raise
