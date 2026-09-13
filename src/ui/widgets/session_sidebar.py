"""左侧会话列表 — 从 chat_page 拆分"""

import threading
import time
import requests
from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMenu,
)
from ._theme import THEME

API_BASE = "http://127.0.0.1:9800"


def _fmt_sidebar_time(ts: str) -> str:
    """侧边栏会话时间：今天显示 HH:MM，往年显示 YYYY-MM-DD，其余 MM-DD HH:MM"""
    if not ts:
        return ""
    s = ts.strip()
    try:
        from datetime import datetime
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
            try:
                dt = datetime.strptime(s[:19], fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return s[:10] if len(s) >= 10 else s
        now = datetime.now()
        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        if dt.year == now.year:
            return dt.strftime("%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return s[:16]


class SessionSidebar(QFrame):
    """左侧的对话列表"""

    session_selected = pyqtSignal(str)
    new_session_requested = pyqtSignal()
    delete_session_requested = pyqtSignal(str)
    sessions_loaded_signal = pyqtSignal(list)

    _last_api_load_time = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.sessions_loaded_signal.connect(self.load_sessions)
        self.setStyleSheet(f"background-color: {THEME['bg_sidebar']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(6)

        title = QLabel("💬 对话列表")
        title.setStyleSheet(
            f"color: {THEME['text_primary']}; font-size: 12px; "
            f"font-weight: bold; padding: 4px 8px;"
        )
        layout.addWidget(title)

        new_btn = QPushButton("＋ 新对话")
        new_btn.setFixedHeight(30)
        new_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        new_btn.clicked.connect(self.new_session_requested.emit)
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['accent2']}; color: #fff; border: none;
                border-radius: 6px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {THEME['accent2']}dd; }}
        """)
        layout.addWidget(new_btn)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent; color: {THEME['text_primary']};
                border: none; font-size: 12px;
            }}
            QListWidget::item {{
                padding: 8px 10px; border-radius: 6px; margin: 1px 2px;
            }}
            QListWidget::item:hover {{ background: {THEME['hover']}; }}
            QListWidget::item:selected {{
                background: {THEME['accent']}33; color: {THEME['accent']};
            }}
        """)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._list, 1)

        self._count_label = QLabel("0 条对话")
        self._count_label.setStyleSheet(
            f"color: {THEME['text_primary']}; font-size: 10px; padding: 4px 8px;"
        )
        layout.addWidget(self._count_label)

        self._sessions = []

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(300, self._load_from_api)

    def _load_from_api(self):
        now = time.time()
        if now - SessionSidebar._last_api_load_time < 1.0:
            logger.debug("[SessionSidebar] 防抖：跳过重复请求")
            return
        SessionSidebar._last_api_load_time = now

        def _do():
            try:
                resp = requests.get(f"{API_BASE}/api/chat/history", timeout=10)
                sessions = resp.json().get("sessions", [])
                logger.info(f"[SessionSidebar] API 返回 {len(sessions)} 个会话")
                self.sessions_loaded_signal.emit(sessions)
            except Exception as e:
                logger.warning(f"[SessionSidebar] 加载失败: {e}")
                SessionSidebar._last_api_load_time = 0
                QTimer.singleShot(2000, self._load_from_api)
        threading.Thread(target=_do, daemon=True).start()

    def load_sessions(self, sessions: list):
        logger.info(f"[SessionSidebar] load_sessions 被调用, {len(sessions)} 个会话")
        self._list.blockSignals(True)
        self._list.setUpdatesEnabled(False)  # 批量添加期间抑制逐项重绘，避免列表卡顿
        self._list.clear()
        self._sessions = sessions
        try:
            for s in sessions:
                title = s.get("title", "对话")
                if len(title) > 20:
                    title = title[:20] + ".."
                sid = s.get("session_id", "")
                updated = s.get("last_activity") or s.get("updated_at", "")
                if updated:
                    updated = _fmt_sidebar_time(updated)
                msg_count = s.get("message_count", 0)
                display = f"💬 {title}"
                if msg_count:
                    display += f"  ⟨{msg_count}⟩"
                if updated:
                    display += f"  {updated}"
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, sid)
                item.setData(Qt.ItemDataRole.UserRole + 1, updated)
                item.setToolTip(f"{title}\n{msg_count} 条消息\n{updated}")
                self._list.addItem(item)
        finally:
            self._list.setUpdatesEnabled(True)  # 恢复重绘，一次性刷新
            self._list.blockSignals(False)
        self._count_label.setText(f"{len(sessions)} 条对话")

    def select_session(self, session_id: str):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == session_id:
                self._list.setCurrentItem(item)
                return

    def add_session(self, session: dict):
        title = session.get("title", "新对话")
        sid = session.get("session_id", "")
        item = QListWidgetItem(f"💬 {title}")
        item.setData(Qt.ItemDataRole.UserRole, sid)
        self._list.insertItem(0, item)
        self._list.setCurrentItem(item)
        self._count_label.setText(f"{self._list.count()} 条对话")


    def remove_session(self, session_id: str):
        """删除后立即从列表移除指定会话"""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == session_id:
                self._list.takeItem(i)
                break
        self._sessions = [s for s in self._sessions if s.get("session_id") != session_id]
        self._count_label.setText(f"{self._list.count()} 条对话")

    def _on_selection_changed(self, current, previous):
        if current:
            sid = current.data(Qt.ItemDataRole.UserRole)
            if sid:
                logger.info(f"[SessionSidebar] 选中会话: {sid[:8]}...")
                self.session_selected.emit(sid)

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        sid = item.data(Qt.ItemDataRole.UserRole)
        if not sid:
            return
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {THEME['bg_card']}; color: {THEME['text_primary']};
                border: 1px solid {THEME['border']}; border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {THEME['hover']}; }}
        """)
        delete_action = menu.addAction("🗑️ 删除此对话")
        action = menu.exec(self._list.mapToGlobal(pos))
        if action == delete_action:
            self.delete_session_requested.emit(sid)
