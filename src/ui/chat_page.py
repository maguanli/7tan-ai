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





# ============================================================

#  Enter 发送输入框（增强版）

# ============================================================

class MessageInput(QPlainTextEdit):

    """支持 Enter 发送、Shift+Enter 换行的输入框"""

    send_triggered = pyqtSignal(str)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls()]
            cursor = self.textCursor()
            cursor.insertText(' '.join(paths))
            event.acceptProposedAction()
        elif event.mimeData().hasText():
            cursor = self.textCursor()
            cursor.insertText(event.mimeData().text())
            event.acceptProposedAction()




    def __init__(self, parent=None):

        super().__init__(parent)

        self.setPlaceholderText("输入消息... (Enter 发送, Shift+Enter 换行, 可拖拽文件)")
        self.setAcceptDrops(True)

        self.setMaximumHeight(120)

        self.setMinimumHeight(48)

        self.setStyleSheet(f"""

            QPlainTextEdit {{

                background-color: {THEME['bg_input']};

                color: {THEME['text_primary']};

                border: 1px solid {THEME['border']};

                border-radius: 8px;

                padding: 10px 14px;

                font-size: 13px;

                selection-background-color: {THEME['accent']};

            }}

            QPlainTextEdit:focus {{

                border-color: {THEME['accent']};

            }}

        """)



    def keyPressEvent(self, event):

        key = event.key()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):

            if event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):

                super().keyPressEvent(event)  # 换行

            else:

                text = self.toPlainText().strip()

                if text:

                    self.send_triggered.emit(text)

                    self.clear()

        else:

            super().keyPressEvent(event)





# ============================================================

#  后台请求线程（带流式支持）

# ============================================================

class ChatWorker(QThread):

    """发送消息并接收回复，支持流式轮询"""

    finished = pyqtSignal(dict)

    streaming = pyqtSignal(dict)  # 用于流式输出

    error = pyqtSignal(str)



    def __init__(self, message, session_id=None, model=None):

        super().__init__()

        self._message = message

        self._session_id = session_id

        self._model = model



    def run(self):

        logger.info("[ChatWorker] run start")

        try:

            data = {"message": self._message}

            if self._session_id:

                data["session_id"] = self._session_id

            if self._model:

                data["model"] = self._model



            resp = requests.post(f"{API_BASE}/api/chat/send", json=data, timeout=610)

            resp.raise_for_status()

            result = resp.json()

            self.finished.emit(result)

        except Exception as e:

            self.error.emit(str(e))





# ============================================================

#  SSE 流式工作线程

# ============================================================

class StreamChatWorker(QThread):

    """SSE 流式读取 — 逐步 yield 思考过程 + 打字机效果"""

    event_received = pyqtSignal(dict)  # 每个 SSE 事件

    finished = pyqtSignal(dict)  # 最终结果

    error = pyqtSignal(str)



    def __init__(self, message, session_id=None, model=None):

        super().__init__()

        self._message = message

        self._session_id = session_id

        self._model = model

        self._abort = False



    def run(self):

        import requests as req

        try:

            data = {"message": self._message}

            if self._session_id:

                data["session_id"] = self._session_id

            if self._model:

                data["model"] = self._model



            with req.post(

                f"{API_BASE}/api/chat/send/stream",

                json=data,

                stream=True,

                timeout=600,

                headers={"Accept": "text/event-stream"}

            ) as resp:

                resp.raise_for_status()

                for line in resp.iter_lines(decode_unicode=True):

                    if self._abort:

                        break

                    if not line or not line.startswith("data: "):

                        continue

                    try:

                        event = json.loads(line[6:])

                        self.event_received.emit(event)

                        if event.get("type") == "done":

                            self.finished.emit(event)

                            return

                        if event.get("type") == "session_id":

                            self.finished.emit(event)

                            return

                        if event.get("type") == "error":

                            self.error.emit(event.get("message", "Unknown error"))

                            return

                    except json.JSONDecodeError:

                        continue

        except Exception as e:

            self.error.emit(str(e))



    def abort(self):

        """终止流式请求"""

        self._abort = True





# ============================================================

#  消息气泡组件

# ============================================================

class MessageBubble(QFrame):

    """单条消息的气泡组件，支持 Markdown、复制、重试"""

    retry_requested = pyqtSignal(str)  # 触发重试



    def __init__(self, role: str, content: str, timestamp: str = "",

                 cost: float = 0, iterations: int = 0,

                 tool_calls: list = None, is_streaming: bool = False,

                 session_id: str = None, parent=None):

        super().__init__(parent)

        logger.info(f"[MessageBubble] init start role={role} len={len(content)}")

        self._role = role

        self._content = content

        self._session_id = session_id

        self._is_streaming = is_streaming



        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)



        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(4)



        # ---- 头部：角色 + 时间戳 ----

        header = QHBoxLayout()

        header.setSpacing(8)



        role_icon = {"user": "🧑", "assistant": "🤖", "system": "⚙️", "error": "❌",

                     "tool_call": "🔧", "tool_result": "📎"}.get(role, "💬")

        role_name = {"user": "你", "assistant": "AI", "system": "系统",

                     "error": "错误", "tool_call": "工具", "tool_result": "结果"}.get(role, "")



        role_label = QLabel(f"{role_icon} <b>{role_name}</b>")

        role_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;")

        header.addWidget(role_label)



        if timestamp:

            ts_label = QLabel(timestamp)

            ts_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 10px;")

            header.addWidget(ts_label)



        header.addStretch()



        # 费用徽章

        if cost > 0 and role == "assistant":

            cost_badge = QLabel(f"💰 ¥{cost:.4f}")

            cost_badge.setStyleSheet(f"""

                QLabel {{

                    background: {THEME['accent2']}44;

                    color: {THEME['accent2']};

                    border: 1px solid {THEME['accent2']}66;

                    border-radius: 8px;

                    padding: 1px 8px;

                    font-size: 10px;

                    font-weight: bold;

                }}

            """)

            header.addWidget(cost_badge)



        if iterations > 1:

            iter_badge = QLabel(f"🔄 {iterations}次")

            iter_badge.setStyleSheet(f"""

                QLabel {{

                    background: {THEME['warning']}33;

                    color: {THEME['warning']};

                    border-radius: 8px;

                    padding: 1px 8px;

                    font-size: 10px;

                }}

            """)

            header.addWidget(iter_badge)



        layout.addLayout(header)



        # ---- 工具调用步骤 ----

        if tool_calls:

            for tc in tool_calls:

                tc_widget = self._build_tool_call_widget(tc)

                layout.addWidget(tc_widget)



        # ---- 消息内容 ----

        self._content_label = QLabel()

        self._content_label.setWordWrap(True)

        self._content_label.setTextFormat(Qt.TextFormat.RichText)

        self._content_label.setOpenExternalLinks(True)

        self._content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)

        self._content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._content_label.setMinimumWidth(0)

        self._content_label.setStyleSheet("border: none; background: transparent;")

        if role == "user":

            bubble_color = THEME['accent']

            text_color = "#000000"

            margin = "0 0 0 60px"

        elif role == "assistant":

            bubble_color = THEME['bg_input']

            text_color = THEME['text_primary']

            margin = "0 60px 0 0"

        elif role == "error":

            bubble_color = f"{THEME['danger']}22"

            text_color = THEME['danger']

            margin = "0"

        else:

            bubble_color = "transparent"

            text_color = THEME['text_primary']

            margin = "0"

        logger.info(f"[MessageBubble] md_to_html start ({len(content)} chars) text_color={text_color}")

        html = self._md_to_html(content, text_color)

        logger.info(f"[MessageBubble] md_to_html done ({len(html)} chars), setting text...")

        self._content_label.setText(html)

        logger.info("[MessageBubble] setText done")



        self.setStyleSheet(f"""

            MessageBubble {{

                background-color: {bubble_color};

                border-radius: 10px;

                padding: 10px 14px;

                margin: {margin};

            }}

        """)

        layout.addWidget(self._content_label)



        # ---- 底部操作栏 ----

        actions = QHBoxLayout()

        actions.setSpacing(6)



        # 复制按钮

        copy_btn = QPushButton("复制")

        copy_btn.setFixedHeight(22)

        copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        copy_btn.clicked.connect(lambda: self._copy_content())

        copy_btn.setStyleSheet(f"""

            QPushButton {{

                background: transparent; color: {text_color};

                border: none; font-size: 10px; padding: 0 6px;

            }}

            QPushButton:hover {{ color: {THEME['accent']}; }}

        """)

        actions.addWidget(copy_btn)

        # edit button
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedHeight(22)
        edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        edit_btn.clicked.connect(lambda: self._edit_message())
        edit_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{text_color};border:none;font-size:10px;padding:0 6px;}}QPushButton:hover{{color:{THEME['accent']};}}")
        actions.addWidget(edit_btn)

        # delete button
        del_btn = QPushButton("删除")
        del_btn.setFixedHeight(22)
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.clicked.connect(lambda: self._delete_self())
        del_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{text_color};border:none;font-size:10px;padding:0 6px;}}QPushButton:hover{{color:{THEME['danger']};}}")
        actions.addWidget(del_btn)

        # 重试按钮（仅 assistant）

        if role == "assistant" and session_id:

            retry_btn = QPushButton("重试")

            retry_btn.setFixedHeight(22)

            retry_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            retry_btn.clicked.connect(lambda: self.retry_requested.emit(self._content))

            retry_btn.setStyleSheet(f"""

                QPushButton {{

                    background: transparent; color: {THEME['text_primary']};

                    border: none; font-size: 10px; padding: 0 6px;

                }}

                QPushButton:hover {{ color: {THEME['warning']}; }}

            """)

            actions.addWidget(retry_btn)



        actions.addStretch()

        layout.addLayout(actions)

        logger.info(f"[MessageBubble] init complete role={role}")



    def _md_to_html(self, md_text: str, text_color: str = None) -> str:
        """Markdown to HTML with pygments syntax highlighting"""
        if not md_text:
            return ""
        try:
            import markdown as _md
            html = _md.markdown(md_text, extensions=['fenced_code', 'tables'], output_format='html')
            html = self._pygments_highlight(html)
            html = html.replace('<a ', '<a style="color:#00d4ff;" ')
            html = html.replace('<table>', '<table style="border-collapse:collapse;margin:8px 0;width:100%;">')
            html = html.replace('<th>', f'<th style="border:1px solid {THEME["border"]};padding:6px 10px;background:{THEME["bg_dark"]};">')
            html = html.replace('<td>', f'<td style="border:1px solid {THEME["border"]};padding:4px 10px;">')
            html = html.replace('<blockquote>', '<blockquote style="border-left:3px solid #00d4ff;padding-left:12px;margin:4px 0;color:#94a3b8;">')
            html = html.replace('<hr>', '<hr style="border-color:#1e293b;margin:8px 0;">')
            html = html.replace('<hr/>', '<hr style="border-color:#1e293b;margin:8px 0;">')
            return f'<div style="color:{text_color or THEME["text_primary"]};font-size:13px;line-height:1.6;word-break:break-word;overflow-wrap:break-word;max-width:100%;">{html}</div>'
        except ImportError:
            return self._md_to_html_safe(md_text, text_color)

    def _md_to_html_safe(self, md_text: str, text_color: str = None) -> str:
        """Fallback: basic HTML escape + <pre> wrapping when markdown lib not available"""
        esc = md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        return f'<div style="color:{text_color or THEME["text_primary"]};font-size:13px;line-height:1.6;word-break:break-word;white-space:pre-wrap;max-width:100%;">{esc}</div>'

    def _pygments_highlight(self, html: str) -> str:

        import re as _re

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

            esc = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

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



    def _build_tool_call_widget(self, tc: dict) -> QFrame:
        """Build collapsible tool-call step widget"""
        w = QFrame()
        w.setStyleSheet(f"""
            QFrame {{
                background: {THEME['bg_dark']}88;
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 4px 8px;
                margin: 2px 0;
            }}
        """)
        wl = QVBoxLayout(w)
        wl.setContentsMargins(6, 3, 6, 3)
        wl.setSpacing(2)

        tool_name = tc.get("tool", tc.get("name", "unknown"))
        status = tc.get("status", "running")
        status_icon = {"running": "...", "success": "OK", "failed": "XX"}.get(status, "...")
        status_color = {"running": THEME["warning"], "success": THEME["success"],
                        "failed": THEME["danger"]}.get(status, THEME["text_primary"])

        # --- top row: status + name + collapse toggle ---
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        icon_lbl = QLabel(status_icon)
        icon_lbl.setStyleSheet(f"color: {status_color}; font-size: 12px; font-weight: bold;")
        top_row.addWidget(icon_lbl)

        name_lbl = QLabel(f"<b>{tool_name}</b>")
        name_lbl.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 12px;")
        top_row.addWidget(name_lbl)

        args = tc.get("args", tc.get("parameters", {}))
        if args:
            args_str = json.dumps(args, ensure_ascii=False)[:80]
            args_lbl = QLabel(f'<span style="color:{THEME["text_muted"]}">{args_str}</span>')
            args_lbl.setStyleSheet("font-size: 11px;")
            top_row.addWidget(args_lbl)

        if status == "running":
            spinner = QLabel("...")
            spinner.setStyleSheet(f"color: {THEME['accent']}; font-size: 16px; font-weight: bold;")
            top_row.addWidget(spinner)

        top_row.addStretch()

        # collapse toggle button
        toggle_btn = QPushButton("-")
        toggle_btn.setFixedSize(22, 22)
        toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']}; border-radius: 4px;
                font-size: 14px; font-weight: bold; padding: 0;
            }}
            QPushButton:hover {{ color: {THEME['accent']}; border-color: {THEME['accent']}; }}
        """)
        top_row.addWidget(toggle_btn)

        wl.addLayout(top_row)

        # --- detail area (collapsible) ---
        detail_w = QFrame()
        detail_w.setStyleSheet("background: transparent;")
        detail_layout = QVBoxLayout(detail_w)
        detail_layout.setContentsMargins(0, 2, 0, 0)
        detail_layout.setSpacing(2)

        summary = tc.get("summary", tc.get("result", ""))
        if summary:
            summary_text = str(summary)[:200]
            summary_lbl = QLabel(f'<span style="color:{THEME["text_secondary"]};font-size:11px;">{summary_text}</span>')
            summary_lbl.setWordWrap(True)
            detail_layout.addWidget(summary_lbl)

        error = tc.get("error", "")
        if error:
            err_lbl = QLabel(f'<span style="color:{THEME["danger"]};font-size:11px;">Error: {error}</span>')
            err_lbl.setWordWrap(True)
            detail_layout.addWidget(err_lbl)

        wl.addWidget(detail_w)
        detail_w.setVisible(True)

        def _toggle():
            visible = detail_w.isVisible()
            detail_w.setVisible(not visible)
            toggle_btn.setText("+" if visible else "-")
        toggle_btn.clicked.connect(_toggle)

        return w

    def _copy_content(self):
        """复制消息内容到剪贴板"""
        QApplication.clipboard().setText(self._content)
        # 短暂反馈
        sender = self.sender()
        if isinstance(sender, QPushButton):
            original = sender.text()
            sender.setText("已复制")
            QTimer.singleShot(1500, lambda: sender.setText(original))
        logger.info("已复制到剪贴板")

    def _edit_message(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑消息")
        dlg.setMinimumSize(420, 220)
        dlg.setStyleSheet(f"background:{THEME['bg_card']};color:{THEME['text_primary']};")
        ly = QVBoxLayout(dlg)
        ed = QPlainTextEdit()
        ed.setPlainText(self._content)
        ed.setStyleSheet(f"background:{THEME['bg_input']};color:{THEME['text_primary']};border:1px solid {THEME['border']};border-radius:6px;")
        ly.addWidget(ed)
        br = QHBoxLayout()
        sv = QPushButton("保存")
        def do_save():
            self._content = ed.toPlainText()
            self.update_content(self._content)
            dlg.accept()
        sv.clicked.connect(do_save)
        cc = QPushButton("取消")
        cc.clicked.connect(dlg.reject)
        br.addWidget(sv); br.addWidget(cc)
        ly.addLayout(br)
        dlg.exec()

    def _delete_self(self):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这条消息吗？删除后无法恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.setVisible(False)
            self.deleteLater()



    def update_content(self, new_content: str, is_streaming: bool = False):

        """更新消息内容（流式输出时自动节流，避免高频渲染崩溃）"""

        self._content = new_content

        self._is_streaming = is_streaming

        if is_streaming:

            # 流式模式：用 timer 节流，最多 100ms 更新一次

            if not hasattr(self, '_update_timer'):

                from PyQt6.QtCore import QTimer

                self._update_timer = QTimer(self)

                self._update_timer.setSingleShot(True)

                self._update_timer.timeout.connect(self._do_update_label)

                self._pending_content = new_content

            self._pending_content = new_content

            if not self._update_timer.isActive():

                self._update_timer.start(100)

        else:

            self._do_update_label()



    def _do_update_label(self):

        """实际执行 QLabel.setText"""

        content = getattr(self, '_pending_content', self._content)

        self._content_label.setText(self._md_to_html(content, "#000000" if self._role == "user" else None))





class SessionSidebar(QFrame):

    """左侧的对话列表"""

    session_selected = pyqtSignal(str)  # session_id

    new_session_requested = pyqtSignal()

    delete_session_requested = pyqtSignal(str)



    sessions_loaded_signal = pyqtSignal(list)


    def __init__(self, parent=None):

        super().__init__(parent)

        self.setFixedWidth(200)

        self.sessions_loaded_signal.connect(self.load_sessions)  # 线程安全

        self.setStyleSheet(f"background-color: {THEME['bg_sidebar']};")



        layout = QVBoxLayout(self)

        layout.setContentsMargins(6, 10, 6, 10)

        layout.setSpacing(6)



        # 标题

        title = QLabel("💬 对话列表")

        title.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 12px; font-weight: bold; padding: 4px 8px;")

        layout.addWidget(title)



        # 新建按钮

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



        # 会话列表

        self._list = QListWidget()

        self._list.setStyleSheet(f"""

            QListWidget {{

                background: transparent; color: {THEME['text_primary']};

                border: none; font-size: 12px;

            }}

            QListWidget::item {{

                padding: 8px 10px;

                border-radius: 6px;

                margin: 1px 2px;

            }}

            QListWidget::item:hover {{

                background: {THEME['hover']};

            }}

            QListWidget::item:selected {{

                background: {THEME['accent']}33;

                color: {THEME['accent']};

            }}

        """)

        self._list.currentItemChanged.connect(self._on_selection_changed)

        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._list.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self._list, 1)



        # 底部信息

        self._count_label = QLabel("0 条对话")

        self._count_label.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 10px; padding: 4px 8px;")

        layout.addWidget(self._count_label)



        self._sessions = []

    def showEvent(self, event):
        super().showEvent(event)
        # 每次显示都重新加载
        QTimer.singleShot(300, self._load_from_api)

    # 模块级防抖：1秒内不重复请求（showEvent 重复触发时）
    _last_api_load_time = 0

    def _load_from_api(self):
        """直接从 API 加载会话列表（后台线程 → 主线程 signal，带防抖）"""
        import threading, requests, time
        now = time.time()
        if now - SessionSidebar._last_api_load_time < 1.0:
            from loguru import logger
            logger.debug("[SessionSidebar] 防抖：跳过重复请求")
            return
        SessionSidebar._last_api_load_time = now

        def _do():
            try:
                resp = requests.get(f"{API_BASE}/api/chat/history", timeout=10)
                sessions = resp.json().get("sessions", [])
                from loguru import logger
                logger.info(f"[SessionSidebar] API 返回 {len(sessions)} 个会话")
                self.sessions_loaded_signal.emit(sessions)  # 线程安全地传到主线程
            except Exception as e:
                from loguru import logger
                logger.warning(f"[SessionSidebar] 加载失败: {e}")
                SessionSidebar._last_api_load_time = 0  # 失败重置，允许重试
                QTimer.singleShot(2000, self._load_from_api)
        threading.Thread(target=_do, daemon=True).start()


    def load_sessions(self, sessions: list):

        """加载会话列表"""
        from loguru import logger
        logger.info(f"[SessionSidebar] load_sessions 被调用, {len(sessions)} 个会话")

        self._list.blockSignals(True)

        self._list.clear()

        self._sessions = sessions

        for s in sessions:

            title = s.get("title", "对话")

            if len(title) > 20:

                title = title[:20] + ".."

            sid = s.get("session_id", "")

            updated = s.get("updated_at", "")

            msg_count = s.get("message_count", 0)



            display = f"💬 {title}"

            if msg_count:

                display += f"  ⟨{msg_count}⟩"



            item = QListWidgetItem(display)

            item.setData(Qt.ItemDataRole.UserRole, sid)

            item.setData(Qt.ItemDataRole.UserRole + 1, updated)

            item.setToolTip(f"{title}\n{msg_count} 条消息\n{updated}")

            self._list.addItem(item)



        self._list.blockSignals(False)

        self._count_label.setText(f"{len(sessions)} 条对话")



    def select_session(self, session_id: str):

        """选中指定会话"""

        for i in range(self._list.count()):

            item = self._list.item(i)

            if item and item.data(Qt.ItemDataRole.UserRole) == session_id:

                self._list.setCurrentItem(item)

                return



    def add_session(self, session: dict):

        """添加一个新会话到列表顶部"""

        title = session.get("title", "新对话")

        sid = session.get("session_id", "")

        item = QListWidgetItem(f"💬 {title}")

        item.setData(Qt.ItemDataRole.UserRole, sid)

        self._list.insertItem(0, item)

        self._list.setCurrentItem(item)

        self._count_label.setText(f"{self._list.count()} 条对话")



    def _on_selection_changed(self, current, previous):

        if current:

            sid = current.data(Qt.ItemDataRole.UserRole)

            if sid:
                from loguru import logger
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

                border: 1px solid {THEME['border']}; border-radius: 6px; padding: 4px;

            }}

            QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}

            QMenu::item:selected {{ background: {THEME['hover']}; }}

        """)

        delete_action = menu.addAction("🗑️ 删除此对话")

        action = menu.exec(self._list.mapToGlobal(pos))

        if action == delete_action:

            self.delete_session_requested.emit(sid)





# ============================================================

#  聊天主体页面（重构后的 ChatPage）

# ============================================================

class ChatPage(QWidget):

    """全新 AI 对话页面 — 左侧会话列表 + 右侧聊天区"""

    session_loaded_signal = pyqtSignal(str, dict)  # (session_id, data)
    error_signal = pyqtSignal(str)  # error message



    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        # 线程安全的信号连接
        self.session_loaded_signal.connect(self._on_session_loaded)
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

        self._messages = []  # 存储消息气泡引用



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



        model_label = QLabel("🤖")

        model_label.setStyleSheet("font-size: 14px;")

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



        send_btn = QPushButton("发送 ▲")

        send_btn.setFixedHeight(30)

        send_btn.setFixedWidth(90)

        send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        send_btn.clicked.connect(lambda: self._send_message(self._input.toPlainText().strip()))

        send_btn.setStyleSheet(f"""

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

        bottom_row.addWidget(send_btn)



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



    def _add_message(self, role: str, content: str, timestamp: str = "",

                     cost: float = 0, iterations: int = 0,

                     tool_calls: list = None, is_streaming: bool = False) -> MessageBubble:

        """添加消息气泡"""

        import sys; sys.stderr.write(f"[_add_message] ENTER role={role}\n"); sys.stderr.flush()

        logger.info(f"[ChatPage] _add_message role={role} content_start={content[:20]}")

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

            session_id=self._current_session_id

        )

        bubble.retry_requested.connect(lambda t, r=role: self._retry_message(t))



        self._messages_layout.addWidget(bubble)

        self._messages.append(bubble)

        self._scroll_to_bottom()

        return bubble



    def _scroll_to_bottom(self):

        """滚动到底部 — 安全版：不调用 processEvents 避免重入崩溃"""

        sb = self._scroll.verticalScrollBar()

        QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))



    def _clear_messages(self):

        """清除所有消息"""

        while self._messages_layout.count() > 0:

            item = self._messages_layout.takeAt(0)

            if item.widget():

                item.widget().deleteLater()

        self._messages.clear()



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

        """在主线程分批渲染消息UI（每批5条，避免阻塞UI线程导致光标转圈）"""

        messages = data.get("messages", [])

        self._current_session_id = session_id

        self._clear_messages()

        self._title_label.setText(f"💬 {data.get('title', '对话')}")

        # 分批渲染：每批 5 条，批次间让 UI 呼吸
        self._pending_messages = messages
        self._msg_render_index = 0
        BATCH_SIZE = 5

        def render_batch():
            i = self._msg_render_index
            batch = self._pending_messages[i:i + BATCH_SIZE]
            for msg in batch:
                role = msg.get("role", "system")
                content = msg.get("content", "")
                if content:
                    self._add_message(role, content)
            self._msg_render_index += BATCH_SIZE
            if self._msg_render_index < len(self._pending_messages):
                # 还有更多消息，下一批用 QTimer 延迟执行
                QTimer.singleShot(10, render_batch)
            else:
                # 全部完成
                self._add_message("system", f"📋 已加载 {len(messages)} 条消息")
                self._pending_messages = []

        if messages:
            QTimer.singleShot(0, render_batch)
        else:
            self._add_message("system", "📋 已加载 0 条消息")



    def _new_session(self):

        """新建对话"""

        self._current_session_id = None

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

                resp = requests.post(f"{API_BASE}/api/chat/send", json=data, timeout=610)

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



        # 刷新会话列表

        if self._current_session_id:

            QTimer.singleShot(500, self._refresh_sessions)



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

            logger.info("[ChatPage] full render ok")



        # 刷新会话列表

        if self._current_session_id:

            QTimer.singleShot(500, self._refresh_sessions)



    def _on_error(self, error_msg: str, thinking_msg=None):

        """处理错误"""

        if thinking_msg:

            self._remove_message(thinking_msg)

        self._add_message("error", f"\u274c \u8bf7\u6c42\u5931\u8d25: {error_msg}")



    def _remove_message(self, msg):

        """移除指定消息"""

        logger.info(f"[ChatPage] _remove_message called")

        if msg and msg in self._messages:

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

