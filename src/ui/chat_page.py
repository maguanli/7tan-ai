"""

ChatPage — 全新 AI 对话界面

===========================================

设计改进：

1. ✅ 左侧会话列表（取代下拉框）

2. ✅ Markdown 渲染（代码块、表格、链接）

3. ✅ 工具调用步骤可视化（实时显示 AI 在做什么）

4. ✅ 每条消息的 复制/重试 按钮

5. ✅ 费用徽章（独立于消息内容）

6. ✅ 流式输出（轮询）

7. ✅ 时间戳

"""

import json

import time

from datetime import datetime



# pygments syntax highlight

from pygments import highlight

from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer

from pygments.formatters import HtmlFormatter

from pygments.util import ClassNotFound



import requests

from loguru import logger

from PyQt6.QtCore import (

    Qt, QThread, pyqtSignal, QTimer, QSize, QUrl,

    QPropertyAnimation, QEasingCurve,

)

from PyQt6.QtGui import (

    QFont, QColor, QPalette, QCursor, QTextCursor,

    QPixmap,

)

from PyQt6.QtWidgets import (

    QApplication, QWidget, QVBoxLayout, QHBoxLayout,

    QPushButton, QLabel, QScrollArea, QFrame, QSplitter,

    QListWidget, QListWidgetItem, QStackedWidget,

    QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox,

    QSizePolicy, QAbstractItemView, QMenu, QDialog,

    QMessageBox, QProgressBar,

)



# ===== 主题色引用（和 app.py 保持一致）=====

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



API_BASE = "http://127.0.0.1:9800"


def _get_chat_timeout() -> int:
    """从配置读取客户端超时 = loop_timeout + 10"""
    try:
        from src.config.loader import load_config
        config = load_config()
        return config.get("agent", {}).get("loop_timeout", 600) + 10
    except Exception:
        return 610





# ============================================================

#  Enter 发送输入框（增强版）

# ---- 从子模块导入已拆分的组件 ----
from .widgets.message_input import MessageInput
from .workers.chat_workers import ChatWorker, StreamChatWorker
from .widgets.message_bubble import MessageBubble
from .widgets.session_sidebar import SessionSidebar

# ============================================================

class ChatPage(QWidget):

    """全新 AI 对话页面 — 左侧会话列表 + 右侧聊天区"""

    session_loaded_signal = pyqtSignal(str, dict)  # (session_id, data)
    error_signal = pyqtSignal(str)  # error message
    messages_parsed_signal = pyqtSignal(str, list, int, int)  # session_id, parsed_msgs, start_idx, total



    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        # 线程安全的信号连接
        self.session_loaded_signal.connect(self._on_session_loaded)
        self.messages_parsed_signal.connect(self._on_messages_parsed)
        self.error_signal.connect(lambda msg: self._add_message("error", msg))



        # ===== 主分屏：左侧会话列 + 右侧聊天区 =====

        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.setHandleWidth(3)

        splitter.setStyleSheet(f"""

            QSplitter::handle {{

                background-color: {THEME['accent']}33;

                border-radius: 1px;

            }}

        """)



        # ---- 左侧：会话列表（可被外部侧边栏替代）----

        self._sidebar = SessionSidebar()

        self._sidebar.session_selected.connect(self._load_session)

        self._sidebar.new_session_requested.connect(self._new_session)

        self._sidebar.delete_session_requested.connect(self._delete_session)

        self._external_sidebar = None  # 外部注入的侧边栏

        splitter.addWidget(self._sidebar)



        # ===== 状态（必须在 _build_chat_panel 之前初始化）=====

        self._current_session_id = None
        self._current_model_key = None
        self._messages = []
        self._message_data = []
        self._current_parsed_data = []  # ALL parsed messages (including unrendered)
        self._full_history_messages = []  # 完整历史消息（用于向上滚动懒加载）
        self._rendered_start = 0
        self._rendered_end = 0
        self._all_rendered = True
        self._lazy_loading = False
        self._batch_rendering = False  # suppress _scroll_to_bottom during batch
        self._HISTORY_CHUNK = 15
        self._LAZY_CHUNK = 10
        self._voice_mode = False  # 语音模式开关
        self._voice_gender = "female"  # 语音性别: female(花颜) / male(云希)
        self._load_voice_gender()  # 从配置恢复上次的语音性别
        self._voice_recording = False  # 是否正在录音
        self._render_queue: list = []
        self._render_timer = None
        self._render_insert_pos: int = 0



        # ---- 右侧：聊天区 ----

        right_panel = self._build_chat_panel()

        splitter.addWidget(right_panel)



        splitter.setSizes([200, 600])

        splitter.setStretchFactor(0, 0)

        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)



        # 初始化时加载模型和会话

        self._load_model_list()

        self._sessions_ever_loaded = False
        self._loading_sessions = False  # 防抖：防止并发加载导致列表被清空



    def attach_external_sidebar(self, sidebar):

        """连接外部会话侧边栏（从 Sidebar 组件传入），隐藏内部侧边栏"""

        self._sidebar.hide()

        # 如果已连接同一个侧边栏，跳过重复连接

        if self._external_sidebar is sidebar:

            return

        # 断开旧的外部侧边栏信号

        if self._external_sidebar is not None:

            try:

                self._external_sidebar.session_selected.disconnect(self._load_session)

                self._external_sidebar.new_session_requested.disconnect(self._new_session)

                self._external_sidebar.delete_session_requested.disconnect(self._delete_session)

            except TypeError:

                pass  # 未连接过，忽略

        self._external_sidebar = sidebar

        sidebar.session_selected.connect(self._load_session)

        sidebar.new_session_requested.connect(self._new_session)

        sidebar.delete_session_requested.connect(self._delete_session)

        # 外部侧边栏挂载后立即加载会话列表
        QTimer.singleShot(200, self._auto_load_sessions)

    def showEvent(self, event):
        super().showEvent(event)
        # 每次显示都重新加载会话列表（带短延迟确保 sidebar 就绪）
        QTimer.singleShot(300, self._auto_load_sessions)


    def _sidebar_ref(self):

        """返回当前活跃的会话侧边栏（外部优先）"""

        return self._external_sidebar or self._sidebar



    # ==================== 右侧聊天面板构建 ====================



    def _build_chat_panel(self) -> QWidget:

        """构建右侧聊天面板"""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(16, 16, 16, 16)

        layout.setSpacing(10)



        # ---- 顶栏：标题 + 模型选择 ----

        top_bar = QHBoxLayout()

        top_bar.setSpacing(8)



        self._title_label = QLabel("💬 AI 对话")
        self._title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['text_primary']};")

        top_bar.addWidget(self._title_label)



        top_bar.addStretch()



        self._ctx_indicator = QLabel("📊 上下文: 0/128K")

        self._ctx_indicator.setStyleSheet(

            f"color: {THEME['text_secondary']}; font-size: 11px; padding: 2px 10px;"

            f"background: {THEME['bg_input']}; border-radius: 10px;"

        )

        self._ctx_indicator.setToolTip("当前对话上下文用量，超过限制后早期消息会被裁减")

        top_bar.addWidget(self._ctx_indicator)



        model_label = QLabel("当前模型")

        model_label.setStyleSheet("font-size: 12px; color: #94a3b8; padding-right: 2px;")

        top_bar.addWidget(model_label)



        self._model_combo = QComboBox()

        self._model_combo.setMinimumWidth(180)

        self._model_combo.setStyleSheet(f"""

            QComboBox {{

                background: {THEME['bg_input']}; color: {THEME['text_primary']};

                border: 1px solid {THEME['border']}; border-radius: 6px;

                padding: 4px 10px; font-size: 12px; min-height: 24px;

            }}

            QComboBox:hover {{ border-color: {THEME['accent']}; }}

            QComboBox::drop-down {{ border: none; width: 20px; }}

            QComboBox QAbstractItemView {{

                background: {THEME['bg_card']}; color: {THEME['text_primary']};

                selection-background-color: {THEME['accent']}44;

                border: 1px solid {THEME['border']}; border-radius: 4px;

            }}

        """)

        self._model_combo.currentIndexChanged.connect(self._on_model_changed)

        top_bar.addWidget(self._model_combo)



        layout.addLayout(top_bar)



        # ---- 消息区 ----

        self._scroll = QScrollArea()

        self._scroll.setWidgetResizable(True)

        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._scroll.setStyleSheet(f"""

            QScrollArea {{

                background-color: {THEME['bg_card']};

                border: 1px solid {THEME['border']};

                border-radius: 10px;

            }}

            QScrollBar:vertical {{

                background: {THEME['bg_dark']}; width: 6px; border-radius: 3px;

            }}

            QScrollBar::handle:vertical {{

                background: {THEME['text_primary']}; border-radius: 3px; min-height: 30px;

            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

        """)



        self._messages_container = QWidget()

        self._messages_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._messages_container.setMinimumWidth(0)

        self._messages_layout = QVBoxLayout(self._messages_container)

        self._messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._messages_layout.setSpacing(8)

        self._messages_layout.setContentsMargins(12, 12, 12, 12)

        # 欢迎消息

        self._show_welcome()



        self._scroll.setWidget(self._messages_container)

        self._scroll.viewport().installEventFilter(self)

        self._messages_container.installEventFilter(self)

        layout.addWidget(self._scroll, 1)



        # ---- 输入区 ----

        input_area = QFrame()

        input_area.setStyleSheet(f"""

            QFrame {{

                background: {THEME['bg_card']};

                border: 1px solid {THEME['border']};

                border-radius: 10px;

                padding: 8px;

            }}

        """)

        input_layout = QVBoxLayout(input_area)

        input_layout.setContentsMargins(8, 8, 8, 8)

        input_layout.setSpacing(8)



        self._input = MessageInput()

        self._input.send_triggered.connect(self._send_message)

        input_layout.addWidget(self._input)



        # 底部行：提示词 + 发送按钮

        bottom_row = QHBoxLayout()

        bottom_row.setSpacing(6)



        hints = ["🎮 找个新游戏", "📊 查统计", "📦 待发布", "🔍 搜资源"]

        for hint in hints:

            h_btn = QPushButton(hint)

            h_btn.setFixedHeight(24)

            h_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            h_btn.clicked.connect(lambda checked, h=hint.split(" ", 1)[1]: self._use_hint(h))

            h_btn.setStyleSheet(f"""

                QPushButton {{

                    background: {THEME['bg_input']};

                    color: {THEME['text_primary']};

                    border: 1px solid {THEME['border']};

                    border-radius: 4px;

                    padding: 2px 8px;

                    font-size: 11px;

                }}

                QPushButton:hover {{

                    background: {THEME['hover']};

                    color: {THEME['text_primary']};

                    border-color: {THEME['accent']}66;

                }}

            """)

            bottom_row.addWidget(h_btn)



        bottom_row.addStretch()

        # ---- 声音性别切换按钮 ----
        self._gender_btn = QPushButton("♀ 女声")
        self._gender_btn.setFixedHeight(30)
        self._gender_btn.setMinimumWidth(85)
        self._gender_btn.setMaximumWidth(140)
        self._gender_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._gender_btn.setCheckable(True)
        self._gender_btn.setChecked(self._voice_gender == "female")
        self._gender_btn.setText("♀ 女声" if self._voice_gender == "female" else "♂ 男声")
        self._gender_btn.clicked.connect(self._toggle_voice_gender)
        self._gender_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_input']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {THEME['accent']}66;
                color: {THEME['accent']};
            }}
            QPushButton:checked {{
                background: #e91e8c;
                color: #fff;
                border-color: #e91e8c;
            }}
            QPushButton:!checked {{
                background: #1976d2;
                color: #fff;
                border-color: #1976d2;
            }}
        """)
        bottom_row.addWidget(self._gender_btn)

        # ---- 语音模式切换按钮 ----
        self._voice_btn = QPushButton("🎤 语音")
        self._voice_btn.setFixedHeight(30)
        self._voice_btn.setMinimumWidth(105)
        self._voice_btn.setMaximumWidth(160)
        self._voice_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._voice_btn.setCheckable(True)
        self._voice_btn.clicked.connect(self._toggle_voice_mode)
        self._voice_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_input']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {THEME['accent']}66;
                color: {THEME['accent']};
            }}
            QPushButton:checked {{
                background: {THEME['accent']};
                color: #000;
                border-color: {THEME['accent']};
                font-weight: bold;
            }}
        """)
        bottom_row.addWidget(self._voice_btn)

        self._send_btn = QPushButton("发送 ▲")
        self._send_btn.setFixedHeight(30)
        self._send_btn.setMinimumWidth(90)
        self._send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._send_btn.clicked.connect(self._on_send_clicked)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME['accent2']}, stop:1 {THEME['accent']});
                color: #fff; border: none; border-radius: 6px;
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
        bottom_row.addWidget(self._send_btn)

        input_layout.addLayout(bottom_row)

        layout.addWidget(input_area)



        return panel



    def _show_welcome(self):

        """显示欢迎消息"""

        welcome = ("<h2 style='text-align:center;color:#3d3d55;margin-top:40px;'>"

                   "👋 欢迎使用 7Tan AI</h2>"

                   "<p style='text-align:center;color:#3d3d55;font-size:13px;'>"

                   "我可以帮你：<br>"

                   "🎮 查找并发布新游戏<br>"

                   "📊 查看系统统计<br>"

                   "📦 管理待发布资源<br>"

                   "🔧 执行自动化任务</p>")

        self._add_message("system", welcome)



    # ==================== 消息管理 ====================

    @staticmethod
    def _pre_parse_single(content: str, role: str) -> str:
        """预解析单条消息的 Markdown→HTML（线程安全，可在后台调用）"""
        if not content:
            return ""
        if role == "user":
            text_color = "#000000"
        elif role == "error":
            text_color = THEME["danger"]
        else:
            text_color = THEME["text_primary"]
        try:
            import markdown as _md
            html = _md.markdown(content, extensions=['fenced_code', 'tables'], output_format='html')
            html = ChatPage._pygments_static(html)
            html = html.replace('<a ', '<a style="color:#00d4ff;" ')
            html = html.replace('<table>', f'<table style="border-collapse:collapse;margin:8px 0;width:100%;">')
            html = html.replace('<th>', f'<th style="border:1px solid {THEME["border"]};padding:6px 10px;background:{THEME["bg_dark"]};">')
            html = html.replace('<td>', f'<td style="border:1px solid {THEME["border"]};padding:4px 10px;">')
            html = html.replace('<blockquote>', '<blockquote style="border-left:3px solid #00d4ff;padding-left:12px;margin:4px 0;color:#94a3b8;">')
            html = html.replace('<img ', '<img style="max-width:100%;height:auto;" ')
            html = html.replace('<hr>', '<hr style="border-color:#1e293b;margin:8px 0;">')
            html = html.replace('<hr/>', '<hr style="border-color:#1e293b;margin:8px 0;">')
            return f'<div style="color:{text_color};font-size:13px;line-height:1.6;word-break:break-word;overflow-wrap:break-word;max-width:100%;">{html}</div>'
        except ImportError:
            esc = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return f'<div style="color:{text_color};font-size:13px;line-height:1.6;white-space:pre-wrap;max-width:100%;">{esc}</div>'

    @staticmethod
    def _pygments_static(html: str) -> str:
        """Pygments 语法高亮（静态版本，线程安全）"""
        import re as _re
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.formatters import HtmlFormatter
        def _hl(match):
            try:
                lang = match.group(1) or "text"
            except IndexError:
                lang = "text"
            code = match.group(2)
            try:
                lexer = get_lexer_by_name(lang, stripall=True)
            except Exception:
                lexer = TextLexer()
            formatter = HtmlFormatter(style="monokai", nowrap=True, noclasses=True)
            highlighted = highlight(code, lexer, formatter)
            return (
                '<div style="position:relative;margin:8px 0;border-radius:6px;overflow:hidden;border:1px solid #3e3d32;">'
                '<div style="background:#272822;color:#75715e;font-size:11px;padding:4px 14px;'
                'display:flex;justify-content:space-between;align-items:center;">'
                '<span style="font-weight:bold;color:#a6e22e;">' + lang + '</span>'
                '<span style="color:#75715e;font-size:10px;">[Ctrl+C 复制]</span>'
                '</div>'
                '<pre style="background:#272822;padding:12px;margin:0;overflow-x:auto;font-size:12px;line-height:1.5;border-radius:0 0 6px 6px;">' + highlighted + '</pre>'
                '</div>'
            )
        return _re.sub(r'<pre><code(?:\s+class="language-(\w+)")?>([\s\S]*?)</code></pre>', _hl, html)

    def _remove_last_system_message(self):
        """移除最后一条系统消息（加载提示等）"""
        if self._messages_layout.count() == 0:
            return
        item = self._messages_layout.takeAt(self._messages_layout.count() - 1)
        if item.widget():
            item.widget().deleteLater()
        if self._messages:
            self._messages.pop()
        if self._message_data:
            self._message_data.pop()
        self._rendered_end = max(0, self._rendered_end - 1)

    def _add_message(self, role: str, content: str, timestamp: str = "",

                     cost: float = 0, iterations: int = 0,

                     tool_calls: list = None, is_streaming: bool = False,
                     pre_parsed_html: str = None) -> MessageBubble:

        """添加消息气泡（延迟渲染：仅可见范围创建重量 Widget）"""
        # 存储原始数据（即使不渲染也保存）
        ts = timestamp or datetime.now().strftime("%H:%M:%S")
        self._message_data.append({
            "role": role, "content": content, "timestamp": ts,
            "cost": cost, "iterations": iterations, "tool_calls": tool_calls,
            "html": pre_parsed_html,
        })
        logger.info(f"[ChatPage] _add_message role={role} data_idx={len(self._message_data)-1}")
        # 新消息始终在末尾渲染，更新范围
        self._rendered_end = len(self._message_data)

        if content.startswith("<h") or content.startswith("<p"):

            # 已经是 HTML（欢迎消息等），用 QLabel

            logger.info("[ChatPage] HTML path")

            msg = QFrame()

            msg.setStyleSheet("background: transparent; padding: 8px;")

            ml = QVBoxLayout(msg)

            ml.setContentsMargins(0, 0, 0, 0)

            label = QLabel(content)

            label.setWordWrap(True)

            label.setTextFormat(Qt.TextFormat.RichText)

            label.setStyleSheet("background: transparent;")

            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            ml.addWidget(label)

            self._messages_layout.addWidget(msg)

            self._messages.append(msg)

            self._scroll_to_bottom()

            return None



        logger.info(f"[ChatPage] creating MessageBubble role={role} len={len(content)}")

        bubble = MessageBubble(

            role=role, content=content,

            timestamp=timestamp or datetime.now().strftime("%H:%M:%S"),

            cost=cost, iterations=iterations,

            tool_calls=tool_calls, is_streaming=is_streaming,

            session_id=self._current_session_id,

            pre_parsed_html=pre_parsed_html

        )

        bubble.retry_requested.connect(lambda t, r=role: self._retry_message(t))



        self._messages_layout.addWidget(bubble)

        self._messages.append(bubble)

        if not self._batch_rendering:
            self._scroll_to_bottom()
            self._update_context_indicator()

        return bubble



    def _scroll_to_bottom(self):

        """滚动到底部 — 安全版：不调用 processEvents 避免重入崩溃"""

        sb = self._scroll.verticalScrollBar()

        QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))



    def _update_context_indicator(self):
        """更新上下文用量指示器"""
        try:
            total_chars = sum(len(m.get("content", "")) for m in self._message_data)
            try:
                import tiktoken
                enc = tiktoken.get_encoding("cl100k_base")
                total_tokens = 0
                for m in self._message_data:
                    content = m.get("content", "")
                    if content:
                        total_tokens += len(enc.encode(content))
            except Exception:
                total_tokens = max(1, total_chars // 2)

            context_window = 128000
            try:
                idx = self._model_combo.currentIndex()
                if idx >= 0:
                    model_key = self._model_combo.itemData(idx)
                    if model_key:
                        from ..database.db import get_ai_config_by_key
                        cfg = get_ai_config_by_key(model_key, mask_secrets=True)
                        if cfg:
                            context_window = cfg.get("context_window", 128000)
            except Exception:
                pass

            if context_window >= 1000:
                ctx_str = f"{context_window // 1000}K"
            else:
                ctx_str = str(context_window)

            if total_tokens >= 10000:
                used_str = f"~{total_tokens // 1000}K"
            elif total_tokens >= 1000:
                used_str = f"~{total_tokens:,}"
            else:
                used_str = str(total_tokens)

            ratio = total_tokens / context_window if context_window > 0 else 0
            if ratio > 0.95:
                color = THEME["danger"]
            elif ratio > 0.80:
                color = THEME["warning"]
            else:
                color = THEME["text_secondary"]

            self._ctx_indicator.setText(f"📊 上下文: {used_str}/{ctx_str}")
            self._ctx_indicator.setStyleSheet(
                f"color: {color}; font-size: 11px; padding: 2px 10px;"
                f"background: {THEME['bg_input']}; border-radius: 10px;"
            )
        except Exception:
            pass


    def _clear_messages(self):

        """清除所有消息"""

                # 停止渐进渲染
        if self._render_timer:
            self._render_timer.stop()
        self._render_queue.clear()
        while self._messages_layout.count() > 0:

            item = self._messages_layout.takeAt(0)

            if item.widget():

                item.widget().deleteLater()

        self._messages.clear()
        self._message_data.clear()
        self._current_parsed_data.clear()
        self._full_history_messages.clear()
        self._rendered_start = 0
        self._rendered_end = 0
        self._all_rendered = True



    # ==================== 模型管理 ====================



    def _load_model_list(self):
        """加载 AI 模型列表（从数据库）"""
        try:
            from ..database.db import get_all_ai_configs, get_active_ai_config
            configs = get_all_ai_configs(mask_secrets=True)
            active_cfg = get_active_ai_config(mask_secrets=True)
            active_key = active_cfg.get("config_key", "") if active_cfg else ""

            self._model_combo.blockSignals(True)
            self._model_combo.clear()
            for cfg in configs:
                key = cfg.get("config_key", "")
                model_name = cfg.get("model", key)
                display = f"{key} ({model_name})"
                if key == active_key:
                    display = f"⭐ {display}"
                self._model_combo.addItem(display, key)

            idx = self._model_combo.findData(active_key)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
                self._current_model_key = active_key
            self._model_combo.blockSignals(False)
        except Exception as e:
            logger.warning(f"加载模型列表失败: {e}")

    def _on_model_changed(self, index):
        """切换 AI 模型"""
        if index < 0:
            return
        config_key = self._model_combo.itemData(index)
        if not config_key or config_key == self._current_model_key:
            return
        try:
            from ..database.db import set_active_ai_config
            from ..agent.model_manager import clear_model_cache
            set_active_ai_config(config_key)
            clear_model_cache()
            self._current_model_key = config_key
            self._add_message("system", f"✅ 已切换到模型: {config_key}")
            # 刷新列表
            self._load_model_list()
        except Exception as e:
            self._add_message("error", f"❌ 切换模型失败: {e}")

    # ==================== 会话管理 ====================



    # 模块级防抖时间戳（与 SessionSidebar 共享防抖逻辑）
    _last_auto_load_time = 0

    def _auto_load_sessions(self, retry=0):

        """自动加载对话列表（后台线程，不阻塞UI，带双重防抖）"""

        import threading, time

        # 防抖1：如果已有加载进行中且非重试，跳过
        if self._loading_sessions and retry == 0:
            logger.debug("[ChatPage] 跳过重复加载请求（已有加载进行中）")
            return

        # 防抖2：1秒内不重复请求（showEvent 与 Sidebar.showEvent 同时触发时）
        now = time.time()
        if retry == 0 and now - ChatPage._last_auto_load_time < 1.0:
            logger.debug("[ChatPage] 防抖：跳过重复请求（1秒内已加载过）")
            return
        ChatPage._last_auto_load_time = now

        self._loading_sessions = True

        def _do_load():

            try:

                resp = requests.get(f"{API_BASE}/api/chat/history", timeout=10)

                sessions = resp.json().get("sessions", [])

                logger.info(f"[ChatPage] 加载到 {len(sessions)} 个会话 (retry={retry})")

                QTimer.singleShot(0, lambda: self._on_sessions_loaded(sessions))

            except Exception as e:

                logger.warning(f"[ChatPage] 自动加载对话失败 (retry={retry}): {e}")

                if retry < 3:

                    QTimer.singleShot(1500, lambda: self._auto_load_sessions(retry + 1))

                else:

                    self._loading_sessions = False

                    ChatPage._last_auto_load_time = 0

                    logger.warning(f"自动加载对话最终失败: {e}")

        threading.Thread(target=_do_load, daemon=True).start()

    def _on_sessions_loaded(self, sessions, attempt=0):

        """在主线程更新会话列表UI"""
        try:
            sidebar = self._sidebar_ref()
            if sidebar is None:
                if attempt < 5:
                    QTimer.singleShot(500, lambda: self._on_sessions_loaded(sessions, attempt + 1))
                    return
                self._loading_sessions = False
                return

            sidebar.load_sessions(sessions)
            logger.info(f"[ChatPage] 会话列表已更新: {len(sessions)} 条")
            if sessions:
                sidebar.select_session(sessions[0].get("session_id", ""))
        except Exception as e:
            logger.warning(f"[ChatPage] _on_sessions_loaded 失败: {e}", exc_info=True)
        finally:
            self._loading_sessions = False



    def _load_session(self, session_id: str):

        """加载指定会话的历史消息（后台线程，不阻塞UI）"""
        from loguru import logger
        logger.info(f"[ChatPage] _load_session 被调用: {session_id[:8]}... current={self._current_session_id[:8] if self._current_session_id else 'None'}...")

        if session_id == self._current_session_id:
            logger.info(f"[ChatPage] 跳过重复加载: {session_id[:8]}...")
            return

        import threading

        def _do_load():

            try:

                resp = requests.get(f"{API_BASE}/api/chat/history?session_id={session_id}", timeout=5)

                data = resp.json()
                logger.info(f"[ChatPage] API返回 {len(data.get('messages',[]))} 条消息")

                # 用 signal 线程安全地更新 UI
                self.session_loaded_signal.emit(session_id, data)

            except Exception as e:
                logger.warning(f"[ChatPage] 加载会话失败: {e}")
                self.error_signal.emit(f"❌ 加载对话失败: {e}")

        threading.Thread(target=_do_load, daemon=True).start()

    def _on_session_loaded(self, session_id: str, data: dict):
        """在主线程渲染历史消息 — 后台预解析 HTML 后渲染"""
        messages = data.get("messages", [])
        self._current_session_id = session_id
        self._clear_messages()
        self._full_history_messages = messages  # 保存完整历史，供向上滚动懒加载使用
        self._title_label.setText(f"💬 {data.get('title', '对话')}")

        if not messages:
            self._add_message("system", "📋 已加载 0 条消息")
            return

        total = len(messages)
        chunk = self._HISTORY_CHUNK
        start_idx = max(0, total - chunk)
        batch = messages[start_idx:]

        # 显示加载提示
        self._add_message("system", f"⏳ 正在准备 {len(batch)} 条消息...")

        # 后台线程预解析 Markdown→HTML
        import threading
        def do_parse():
            parsed = []
            for msg in batch:
                role = msg.get("role", "system")
                content = msg.get("content", "")
                html = self._pre_parse_single(content, role) if content else None
                parsed.append({
                    "role": role, "content": content,
                    "html": html,
                    "timestamp": msg.get("timestamp", ""),
                    "cost": msg.get("cost", 0),
                    "tool_calls": msg.get("tool_calls"),
                })
            self.messages_parsed_signal.emit(session_id, parsed, start_idx, total)

        threading.Thread(target=do_parse, daemon=True).start()

    def _on_messages_parsed(self, session_id: str, parsed: list, start_idx: int, total: int):
        """后台解析完成后，在主线程渐进渲染（先秒出5条，再逐条渲染）"""
        if session_id != self._current_session_id:
            return

        self._current_parsed_data = parsed
        self._remove_last_system_message()

        self._rendered_start = start_idx
        self._rendered_end = start_idx
        self._all_rendered = (start_idx == 0)

        # 先渲染提示（如果有）
        self._batch_rendering = True
        self._scroll.setUpdatesEnabled(False)
        try:
            if start_idx > 0:
                self._add_message("system",
                    f"📜 以上还有 {start_idx} 条历史消息（向上滚动自动加载）")
        finally:
            self._batch_rendering = False
            self._scroll.setUpdatesEnabled(True)

        # 过滤有效消息
        valid = [m for m in parsed if m.get("content")]
        FIRST = min(5, len(valid))

        # 第一批：秒渲 5 条
        self._scroll.setUpdatesEnabled(False)
        try:
            for msg in valid[:FIRST]:
                self._add_message(
                    msg["role"], msg["content"],
                    timestamp=msg.get("timestamp", ""),
                    cost=msg.get("cost", 0),
                    tool_calls=msg.get("tool_calls"),
                    pre_parsed_html=msg.get("html"),
                )
                self._rendered_end += 1
        finally:
            self._scroll.setUpdatesEnabled(True)
            self._messages_container.adjustSize()
            self._messages_container.updateGeometry()
            QTimer.singleShot(30, self._scroll_to_bottom)

        # 剩余 → 渐进队列（每 10ms 渲染 1 条）
        if len(valid) > FIRST:
            self._render_queue = valid[FIRST:]
            self._render_insert_pos = -1
            if self._render_timer is None:
                self._render_timer = QTimer(self)
                self._render_timer.timeout.connect(self._render_next_batch)
            self._render_timer.start(10)
        else:
            self._finish_render()

    def _render_next_batch(self):
        """渐进渲染队列中的下一条消息（仅限末尾追加）"""
        if not self._render_queue:
            if self._render_timer:
                self._render_timer.stop()
            self._finish_render()
            return
        msg = self._render_queue.pop(0)
        self._scroll.setUpdatesEnabled(False)
        try:
            self._add_message(
                msg["role"], msg["content"],
                timestamp=msg.get("timestamp", ""),
                cost=msg.get("cost", 0),
                tool_calls=msg.get("tool_calls"),
                pre_parsed_html=msg.get("html"),
            )
            self._rendered_end += 1
        finally:
            self._scroll.setUpdatesEnabled(True)
        if not self._render_queue:
            if self._render_timer:
                self._render_timer.stop()
            self._finish_render()

    def _finish_render(self):
        """渐进渲染完成后的收尾"""
        self._rendered_end = len(self._message_data)
        self._messages_container.adjustSize()
        self._messages_container.updateGeometry()

        if not self._all_rendered:
            try:
                self._scroll.verticalScrollBar().valueChanged.disconnect(
                    self._on_history_scroll)
            except TypeError:
                pass
            self._scroll.verticalScrollBar().valueChanged.connect(
                self._on_history_scroll)
        self._update_context_indicator()

    def _scroll_to_bottom(self):
        scroll = self._scroll
        vbar = scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())
        self._messages_container.adjustSize()
        self._messages_container.updateGeometry()

    def _on_history_scroll(self, value: int):
        """滚动到顶部时自动加载更多历史消息"""
        if self._all_rendered or self._lazy_loading:
            return
        if value > 80:  # 距离顶部 80px 以内触发
            return
        self._lazy_loading = True
        self._load_more_history()

    def _load_more_history(self):
        """加载更早的历史消息（每次 LAZY_CHUNK 条）"""
        if self._rendered_start <= 0:
            self._all_rendered = True
            self._lazy_loading = False
            return

        chunk = self._LAZY_CHUNK
        new_start = max(0, self._rendered_start - chunk)

        # 1) 优先从预解析缓存读取
        parsed_slice = self._current_parsed_data[new_start:self._rendered_start] if self._current_parsed_data else []
        old_messages = []
        for msg in reversed(parsed_slice):
            md = {"role": msg["role"], "content": msg["content"], "timestamp": msg.get("timestamp", ""), "cost": msg.get("cost", 0), "tool_calls": msg.get("tool_calls"), "html": msg.get("html")}
            old_messages.append(md)
            self._message_data.insert(new_start, md)

        # 2) 缓存不够？从完整历史列表实时解析
        if not old_messages and self._full_history_messages:
            raw_slice = self._full_history_messages[new_start:self._rendered_start]
            for msg in reversed(raw_slice):
                role = msg.get("role", "system")
                content = msg.get("content", "")
                html = self._pre_parse_single(content, role) if content else None
                md = {"role": role, "content": content, "timestamp": msg.get("timestamp", ""), "cost": msg.get("cost", 0), "tool_calls": msg.get("tool_calls"), "html": html}
                old_messages.append(md)
                self._message_data.insert(new_start, md)

        # 3) 仍为空则放弃
        if not old_messages:
            self._all_rendered = True
            self._lazy_loading = False
            return

        # 记录当前滚动位置，用于加载后恢复
        sb = self._scroll.verticalScrollBar()
        old_max = sb.maximum()

        self._scroll.setUpdatesEnabled(False)
        try:
            # 插入到布局顶部（old_messages 已是旧→新顺序）
            for md in old_messages:
                self._insert_message_at_top(md)

            self._rendered_start = new_start
            if new_start <= 0:
                self._all_rendered = True
                # 移除"加载更多"提示
                for i in range(self._messages_layout.count()):
                    w = self._messages_layout.itemAt(i).widget()
                    if w and hasattr(w, '_content') and '以上还有' in getattr(w, '_content', ''):
                        self._messages.remove(w)
                        item = self._messages_layout.takeAt(i)
                        if item.widget():
                            item.widget().deleteLater()
                        # 同步清理 _message_data
                        for j, md in enumerate(self._message_data):
                            if md.get("role") == "system" and '以上还有' in md.get("content", ""):
                                self._message_data.pop(j)
                                self._rendered_end -= 1
                                self._rendered_start -= 1
                                break
                        break
        finally:
            self._scroll.setUpdatesEnabled(True)
            self._messages_container.adjustSize()
            self._messages_container.updateGeometry()

        # 恢复滚动位置（新消息在老消息之上，需要补偿偏移）
        new_max = sb.maximum()
        delta = new_max - old_max
        QTimer.singleShot(50, lambda: sb.setValue(sb.value() + delta))
        self._lazy_loading = False

    def _insert_message_at_top(self, md: dict):
        """在布局顶部插入一条消息"""
        # 找到第一个非 system 提示的 widget 位置
        insert_pos = 0
        for i in range(self._messages_layout.count()):
            w = self._messages_layout.itemAt(i).widget()
            if w and hasattr(w, '_content') and '以上还有' in getattr(w, '_content', ''):
                insert_pos = i + 1
                break

        bubble = MessageBubble(
            role=md["role"], content=md["content"],
            timestamp=md.get("timestamp", ""),
            cost=md.get("cost", 0), iterations=md.get("iterations", 0),
            tool_calls=md.get("tool_calls"), is_streaming=False,
            session_id=self._current_session_id,
            pre_parsed_html=md.get("html")
        )
        bubble.retry_requested.connect(lambda t, r=md["role"]: self._retry_message(t))
        self._messages_layout.insertWidget(insert_pos, bubble)
        self._messages.insert(insert_pos, bubble)




    def _new_session(self):
        """新建对话"""
        self._current_session_id = None
        # 断开历史滚动加载
        try:
            self._scroll.verticalScrollBar().valueChanged.disconnect(
                self._on_history_scroll)
        except TypeError:
            pass
        self._clear_messages()

        self._show_welcome()

        self._title_label.setText("💬 新对话")



    def _delete_session(self, session_id: str):

        """删除对话"""

        reply = QMessageBox.question(self, "确认删除",

            "确定要删除此对话吗？\n此操作不可撤销。",

            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply != QMessageBox.StandardButton.Yes:

            return

        import threading

        def _do_delete():

            try:

                requests.delete(f"{API_BASE}/api/chat/session/{session_id}", timeout=5)

                QTimer.singleShot(0, lambda: self._new_session())

                QTimer.singleShot(300, self._auto_load_sessions)

            except Exception as e:

                QTimer.singleShot(0, lambda: self._add_message("error", f"❌ 删除失败: {e}"))

        threading.Thread(target=_do_delete, daemon=True).start()



    # ==================== 消息收发 ====================

    def _toggle_voice_gender(self):
        """切换男女声"""
        # 直接基于当前性别取反，不依赖 isChecked()
        if self._voice_gender == "female":
            self._voice_gender = "male"
            self._gender_btn.setText("♂ 男声")
            self._gender_btn.setChecked(False)
        else:
            self._voice_gender = "female"
            self._gender_btn.setText("♀ 女声")
            self._gender_btn.setChecked(True)

        msg = f"[Voice] 切换为: {self._voice_gender}"
        print(msg)
        logger.info(msg)

        # 持久化保存
        self._save_voice_gender()

        try:
            from data.plugins.tts_piper.tools import tts_set_gender
            result = tts_set_gender(self._voice_gender)
            msg2 = f"[Voice] TTS 引擎切换结果: {result}"
            print(msg2)
            logger.info(msg2)
        except Exception as e:
            msg3 = f"[Voice] TTS 引擎切换失败: {e}"
            print(msg3)
            logger.warning(msg3)

    # ---- 语音设置持久化（纯数据库 app_settings 表）----

    @staticmethod
    def _db_path():
        """games.db 路径 — 基于 __file__，不受工作目录影响"""
        from pathlib import Path
        return str(Path(__file__).resolve().parent.parent.parent / "data" / "games.db")

    def _db_set(self, key, value):
        """写入一条设置到 app_settings 表（独立短连接，立即提交）"""
        import sqlite3
        con = sqlite3.connect(self._db_path())
        try:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)"
            )
            cur.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
            con.commit()
        finally:
            con.close()

    def _db_get(self, key, default=""):
        """从 app_settings 表读取一条设置（独立短连接）"""
        import sqlite3
        try:
            con = sqlite3.connect(self._db_path())
            try:
                cur = con.cursor()
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)"
                )
                cur.execute("SELECT value FROM app_settings WHERE key=?", (key,))
                row = cur.fetchone()
                return row[0] if row else default
            finally:
                con.close()
        except Exception as e:
            print(f"[Voice] 数据库读取异常: {type(e).__name__}: {e}")
            logger.error(f"[Voice] 数据库读取异常: {type(e).__name__}: {e}")
            return default

    def _load_voice_gender(self):
        """启动时从数据库恢复语音设置"""
        print(f"[Voice] __file__ = {__file__}")
        logger.info(f"[Voice] __file__ = {__file__}")
        print(f"[Voice] 数据库路径 = {self._db_path()}")
        logger.info(f"[Voice] 数据库路径 = {self._db_path()}")
        gender = self._db_get("voice_gender", "")
        mode = self._db_get("voice_mode", "")
        print(f"[Voice] 数据库读取: gender={gender!r}, mode={mode!r}")
        logger.info(f"[Voice] 数据库读取: gender={gender!r}, mode={mode!r}")

        if gender in ("female", "male"):
            self._voice_gender = gender
        else:
            self._voice_gender = "female"
        self._voice_mode = (str(mode).lower() == "true")
        print(f"[Voice] 已从数据库恢复: gender={self._voice_gender}, mode={self._voice_mode}")
        logger.info(f"[Voice] 已从数据库恢复: gender={self._voice_gender}, mode={self._voice_mode}")

        try:
            from data.plugins.tts_piper.tools import tts_set_gender
            tts_set_gender(self._voice_gender)
        except Exception as e:
            print(f"[Voice] TTS引擎设置失败: {e}")
            logger.warning(f"[Voice] TTS引擎设置失败: {e}")

    def _save_voice_gender(self):
        """把当前语音设置写入数据库（立即生效，供下次启动读取）"""
        print(f"[Voice] 保存到数据库路径 = {self._db_path()}")
        logger.info(f"[Voice] 保存到数据库路径 = {self._db_path()}")
        try:
            self._db_set("voice_gender", self._voice_gender)
            self._db_set("voice_mode", "true" if self._voice_mode else "false")
            # 独立连接读回验证
            verify = self._db_get("voice_gender", "")
            if verify == self._voice_gender:
                print(f"[Voice] 数据库保存成功并验证通过: gender={verify}, mode={self._voice_mode}")
                logger.info(f"[Voice] 数据库保存成功并验证通过: gender={verify}, mode={self._voice_mode}")
            else:
                print(f"[Voice] 数据库验证失败! 写入={self._voice_gender}, 读回={verify}")
                logger.error(f"[Voice] 数据库验证失败! 写入={self._voice_gender}, 读回={verify}")
        except Exception as e:
            print(f"[Voice] 数据库保存异常: {type(e).__name__}: {e}")
            logger.error(f"[Voice] 数据库保存异常: {type(e).__name__}: {e}")


    def closeEvent(self, event):
        """窗口关闭时兜底保存语音设置到数据库"""
        try:
            self._save_voice_gender()
            print("[Voice] closeEvent 已保存语音设置")
            logger.info("[Voice] closeEvent 已保存语音设置")
        except Exception as e:
            print(f"[Voice] closeEvent 保存异常: {e}")
            logger.warning(f"[Voice] closeEvent 保存异常: {e}")
        try:
            super().closeEvent(event)
        except Exception:
            pass

    def _toggle_voice_mode(self):
        """切换语音/文字模式"""
        self._voice_mode = self._voice_btn.isChecked()
        if self._voice_mode:
            self._voice_btn.setText("🎤 语音中")
            self._send_btn.setText("🎤 录音发送")
            self._input.setPlaceholderText("语音模式：点击录音按钮开始说话...")
            # 🎤 设置 Agent 语音回调：让 Agent 中间消息也能朗读
            from ..agent.agent_loop import set_agent_speak_callback
            set_agent_speak_callback(self._speak_response)
        else:
            self._voice_btn.setText("🎤 语音")
            self._send_btn.setText("发送 ▲")
            self._input.setPlaceholderText("输入消息... (Enter 发送, Shift+Enter 换行, 可拖拽文件)")
            # 🎤 清除 Agent 语音回调
            from ..agent.agent_loop import set_agent_speak_callback
            set_agent_speak_callback(None)

        # 持久化语音模式
        self._save_voice_gender()

    def _on_send_clicked(self):
        """发送按钮点击：语音模式走录音，文字模式走发送"""
        if self._voice_mode:
            self._voice_record_and_send()
        else:
            text = self._input.toPlainText().strip()
            if text:
                self._send_message(text)

    def _voice_record_and_send(self):
        """录音 → STT → 发送"""
        if self._voice_recording:
            return  # 防止重复点击
        
        self._voice_recording = True
        self._send_btn.setEnabled(False)
        self._send_btn.setText("🔴 录音中...")
        self._add_message("system", "🎤 正在录音，请说话...（5 秒后自动停止）")
        
        import threading
        def _record_and_send():
            try:
                import sounddevice as sd
                import numpy as np
                import tempfile
                import wave
                import subprocess
                import os
                
                # 录音参数
                duration = 5  # 秒
                sample_rate = 16000
                channels = 1
                
                # 录音
                audio = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=channels,
                    dtype='int16'
                )
                sd.wait()
                
                # 保存为 WAV
                tmp_wav = os.path.join(tempfile.gettempdir(), '7tan_voice.wav')
                with wave.open(tmp_wav, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio.tobytes())
                
                # Whisper STT
                whisper_exe = r'G:\whisper_cpp\Release\whisper-cli.exe'
                whisper_model = r'G:\whisper_cpp\models\ggml-small.bin'
                result = subprocess.run(
                    [whisper_exe, '-m', whisper_model, '-f', tmp_wav, '-l', 'zh', '--no-timestamps'],
                    capture_output=True, text=True, timeout=30
                )
                
                # 提取识别文本
                recognized = result.stdout.strip()
                if not recognized:
                    recognized = result.stderr.strip()
                
                # 清理临时文件
                try:
                    os.remove(tmp_wav)
                except:
                    pass
                
                if recognized:
                    # 用 signal 在主线程设置文本并发送
                    def _send_recognized():
                        self._input.setPlainText(recognized)
                        self._send_message(recognized)
                    QTimer.singleShot(50, _send_recognized)
                else:
                    QTimer.singleShot(0, lambda: self._add_message("error", "❌ 未识别到语音内容，请重试"))
                    
            except Exception as e:
                QTimer.singleShot(0, lambda: self._add_message("error", f"❌ 录音失败: {e}"))
            finally:
                def _reset():
                    self._voice_recording = False
                    self._send_btn.setEnabled(True)
                    if self._voice_mode:
                        self._send_btn.setText("🎤 录音发送")
                    else:
                        self._send_btn.setText("发送 ▲")
                QTimer.singleShot(0, _reset)
        
        threading.Thread(target=_record_and_send, daemon=True).start()

    def _send_message(self, text: str = None):

        """发送消息（支持流式输出 + 思考过程展示）"""

        if text is None:

            text = self._input.toPlainText().strip()

        if not text:

            return



        self._input.clear()

        self._add_message("user", text)



        # 获取当前模型

        model = None

        idx = self._model_combo.currentIndex()

        if idx >= 0:

            model_key = self._model_combo.itemData(idx)

            if model_key:

                from ..database.db import get_ai_config_by_key

                cfg = get_ai_config_by_key(model_key, mask_secrets=False)

                if cfg:

                    model = cfg.get("model", model_key)

                else:

                    model = model_key



        # 用 Python 原生线程 + 轮询，避免 QThread 信号导致 Qt C++ 栈崩溃

        import threading

        thinking_msg = self._add_message("system", "\u23f3 AI \u601d\u8003\u4e2d...")



        data = {"message": text}

        if self._current_session_id:

            data["session_id"] = self._current_session_id

        if model:

            data["model"] = model



        self._pending_result = None

        self._pending_error = None

        self._poll_thinking_msg = thinking_msg  # 保存引用



        def _do_request():

            try:

                resp = requests.post(f"{API_BASE}/api/chat/send", json=data, timeout=_get_chat_timeout())

                resp.raise_for_status()

                self._pending_result = resp.json()

            except Exception as e:

                self._pending_error = str(e)



        threading.Thread(target=_do_request, daemon=True).start()



        # 用实例方法轮询，避免闭包问题

        self._poll_timer = QTimer(self)

        self._poll_timer.timeout.connect(self._poll_response)

        self._poll_timer.start(500)



    def _poll_response(self):

        """轮询检查后台线程的请求结果"""

        if self._pending_result is not None:

            result = self._pending_result

            self._pending_result = None

            self._poll_timer.stop()

            self._on_response(result, self._poll_thinking_msg)

        elif self._pending_error is not None:

            error = self._pending_error

            self._pending_error = None

            self._poll_timer.stop()

            self._on_error(error, self._poll_thinking_msg)



    def _send_streaming(self, text: str, model: str = None):

        """使用 SSE 流式发送消息，展示思考过程 + 打字机效果"""

        # 创建"思考中"状态栏（将在收到第一个事件后保留）

        self._streaming_assistant_bubble = None  # AI 回复气泡

        self._streaming_thinking_container = None  # 思考过程容器

        self._streaming_tool_calls = []  # 工具调用列表

        self._streaming_text = ""  # 累积文本

        self._streaming_session_id = self._current_session_id



        # 创建思考过程气泡

        self._streaming_thinking_bubble = self._add_message("system", "\u23f3 AI \u6b63\u5728\u601d\u8003...")



        # 启动 SSE 流式线程

        self._stream_worker = StreamChatWorker(text, self._current_session_id, model)

        self._stream_worker.event_received.connect(self._on_stream_event)

        self._stream_worker.finished.connect(self._on_stream_finished)

        self._stream_worker.error.connect(lambda e: self._on_error(e, self._streaming_thinking_bubble))

        self._stream_worker.start()



    def _on_stream_event(self, event: dict):

        """处理流式事件 — 实时更新思考过程和内容"""

        etype = event.get("type", "")



        if etype == "thinking":

            # 更新思考状态

            if self._streaming_thinking_bubble:

                msg = event.get("message", "")

                self._streaming_thinking_bubble.update_content(msg)



        elif etype == "iteration":

            # 显示迭代进度

            it = event.get("iteration", 1)

            total = event.get("max_iterations", 80)

            if self._streaming_thinking_bubble:

                self._streaming_thinking_bubble.update_content(f"\ud83d\udd04 \u7b2c {it}/{total} \u8f6e\u63a8\u7406...")



        elif etype == "tool_call":

            # 实时显示工具调用

            tool_name = event.get("tool_name", "unknown")

            args = event.get("args", {})

            tc = {"tool": tool_name, "args": args, "status": "running"}

            self._streaming_tool_calls.append(tc)

            self._update_streaming_display()



        elif etype == "tool_result":

            # 更新工具调用状态

            tool_name = event.get("tool_name", "")

            is_error = event.get("error", False)

            summary = event.get("summary", "")

            for tc in self._streaming_tool_calls:

                if tc.get("tool") == tool_name and tc.get("status") == "running":

                    tc["status"] = "failed" if is_error else "success"

                    tc["summary"] = summary

            self._update_streaming_display()



        elif etype == "text_chunk":

            # 打字机效果 — 逐段追加文本

            chunk = event.get("content", "")

            self._streaming_text += chunk

            if self._streaming_assistant_bubble is None:

                # 第一个文本块到达，创建 AI 回复气泡（带工具调用）

                self._streaming_assistant_bubble = self._add_message(

                    "assistant", self._streaming_text,

                    is_streaming=True,

                    tool_calls=self._streaming_tool_calls,

                    session_id=self._streaming_session_id,

                )

            else:

                self._streaming_assistant_bubble.update_content(

                    self._streaming_text, is_streaming=True

                )

            # 滚动到底部

            self._scroll_to_bottom()



        elif etype == "cost":

            # 费用更新（最终会在 done 中设置）

            pass



        elif etype == "session_id":

            self._streaming_session_id = event.get("session_id", self._streaming_session_id)

            self._current_session_id = self._streaming_session_id



    def _update_streaming_display(self):

        """更新当前展示的工具调用步骤"""

        # 如果已经有了 assistant 气泡，更新它的 tool_calls

        if self._streaming_assistant_bubble and hasattr(self._streaming_assistant_bubble, '_tool_calls'):

            pass  # 气泡已创建时携带了工具调用



        # 如果还没有 assistant 气泡，但在思考过程中有工具调用

        # 那就更新 thinking 气泡显示工具调用信息

        if self._streaming_thinking_bubble and self._streaming_tool_calls:

            active_tools = [t for t in self._streaming_tool_calls if t.get("status") == "running"]

            if active_tools:

                names = ", ".join([t["tool"] for t in active_tools])

                self._streaming_thinking_bubble.update_content(

                    f"\ud83d\udd04 \u6b63\u5728\u8c03\u7528\u5de5\u5177: {names}"

                )



    def _on_stream_finished(self, data: dict):

        """流式响应完成"""

        # 移除 thinking 气泡

        if self._streaming_thinking_bubble:

            self._remove_message(self._streaming_thinking_bubble)

            self._streaming_thinking_bubble = None



        success = data.get("success", True)

        result = data.get("result", self._streaming_text)

        cost = data.get("cost", 0)

        iterations = data.get("iterations", 0)

        session_id = data.get("session_id", self._streaming_session_id)



        if session_id:

            self._current_session_id = session_id



        if not success:

            self._add_message("error", result, cost=cost, iterations=iterations)

        elif self._streaming_assistant_bubble:

            # 更新最终状态（去掉流式标记、更新费用）

            self._streaming_assistant_bubble._is_streaming = False

            self._streaming_assistant_bubble.update_content(result, is_streaming=False)

            # 更新 tool_calls 最终状态

            if self._streaming_tool_calls:

                # 清除未完成的 running 状态

                for tc in self._streaming_tool_calls:

                    if tc.get("status") == "running":

                        tc["status"] = "failed"

            self._streaming_assistant_bubble = None

        self._update_context_indicator()

        # 刷新会话列表

        if self._current_session_id:

            QTimer.singleShot(500, self._refresh_sessions)

        # 🎤 语音模式：后台线程朗读（合成+播放全在后台，不阻塞UI）
        if self._voice_mode and not self._voice_recording and success and result:
            import threading
            threading.Thread(target=self._speak_response, args=(result,), daemon=True).start()



    def _on_response(self, data, thinking_msg=None):

        """处理回复（传统模式 fallback）"""

        logger.info("[ChatPage] _on_response called")

        # 删除 thinking 指示器

        if thinking_msg:

            self._remove_message(thinking_msg)

        

        self._current_session_id = data.get("session_id", self._current_session_id)

        result = data.get("result", "\u65e0\u54cd\u5e94")

        cost = data.get("cost", 0)

        iterations = data.get("iterations", 0)

        success = data.get("success", False)

        logger.info(f"[ChatPage] result len={len(result)} cost={cost} iterations={iterations}")



        if not success:

            self._add_message("error", f"\u274c {result}", cost=cost, iterations=iterations)

        else:

            logger.info("[ChatPage] calling _add_message assistant")

            self._add_message("assistant", result, cost=cost, iterations=iterations)
            self._update_context_indicator()

            logger.info("[ChatPage] full render ok")



        # 刷新会话列表

        if self._current_session_id:

            QTimer.singleShot(500, self._refresh_sessions)

        # 🎤 语音模式：后台线程朗读（合成+播放全在后台，不阻塞UI）
        if self._voice_mode and not self._voice_recording and success and result:
            import threading
            threading.Thread(target=self._speak_response, args=(result,), daemon=True).start()




    def _speak_response(self, text: str):
        """后台线程：语音模式下朗读 AI 回复"""
        logger.info(f"[TTS] _speak_response START: text_len={len(text) if text else 0}")
        try:
            from data.plugins.tts_piper.tools import tts_speak
            result = tts_speak(text, play=True, strip_code=True)
            logger.info(f"[TTS] _speak_response OK: {result}")
        except Exception as e:
            logger.error(f"[TTS] 朗读失败: {e}", exc_info=True)

    def _on_error(self, error_msg: str, thinking_msg=None):

        """处理错误"""

        if thinking_msg:

            self._remove_message(thinking_msg)

        self._add_message("error", f"\u274c \u8bf7\u6c42\u5931\u8d25: {error_msg}")



    def _remove_message(self, msg):
        """移除指定消息（同步清理数据）"""
        logger.info(f"[ChatPage] _remove_message called")
        if msg and msg in self._messages:
            # 从数据层移除
            msg_idx = self._messages.index(msg)
            if msg_idx < len(self._message_data):
                self._message_data.pop(msg_idx)
                if self._rendered_end > msg_idx:
                    self._rendered_end -= 1
                if self._rendered_start > msg_idx:
                    self._rendered_start -= 1
            self._messages.remove(msg)
            idx = self._messages_layout.indexOf(msg)
            if idx >= 0:
                item = self._messages_layout.takeAt(idx)
                if item.widget():
                    item.widget().deleteLater()



    def _retry_message(self, content: str):

        """重试 — 重新发送消息"""

        self._send_message(content)



    def _refresh_sessions(self):

        """刷新会话列表"""

        try:

            resp = requests.get(f"{API_BASE}/api/chat/history", timeout=5)

            sessions = resp.json().get("sessions", [])

            if sessions:

                sidebar = self._sidebar_ref()

                if sidebar is not None:

                    sidebar.load_sessions(sessions)

                    logger.debug(f"[ChatPage] 会话列表已刷新: {len(sessions)} 条")

        except Exception:
            logger.warning("加载会话历史失败", exc_info=True)



    def eventFilter(self, obj, event):

        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.Resize:

            if obj is self._scroll.viewport() or obj is self._messages_container:

                vp_w = self._scroll.viewport().width()

                if vp_w > 0:

                    self._messages_container.setFixedWidth(vp_w)

        return super().eventFilter(obj, event)



    def _use_hint(self, text):

        """使用快捷提示"""

        self._input.setPlainText(text)

        self._send_message(text)

