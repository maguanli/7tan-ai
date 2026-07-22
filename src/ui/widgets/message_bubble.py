"""消息气泡组件 — 从 chat_page 拆分"""

import json
from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QDialog, QMessageBox, QApplication,
    QSizePolicy,
)

# pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter

from ._theme import THEME



class MessageBubble(QFrame):

    """单条消息的气泡组件，支持 Markdown、复制、重试"""

    retry_requested = pyqtSignal(str)  # 触发重试



    def __init__(self, role: str, content: str, timestamp: str = "",

                 cost: float = 0, iterations: int = 0,

                 tool_calls: list = None, is_streaming: bool = False,

                 session_id: str = None, pre_parsed_html: str = None,
                 parent=None):

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

        if pre_parsed_html:
            html = pre_parsed_html
        else:
            html = self._md_to_html(content, text_color)

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
            html = html.replace('<table>', '<table style="border-collapse:collapse;margin:8px 0;width:100%;table-layout:fixed;word-break:break-all;">')
            html = html.replace('<th>', f'<th style="border:1px solid {THEME["border"]};padding:6px 10px;background:{THEME["bg_dark"]};">')
            html = html.replace('<td>', f'<td style="border:1px solid {THEME["border"]};padding:4px 10px;">')
            html = html.replace('<blockquote>', '<blockquote style="border-left:3px solid #00d4ff;padding-left:12px;margin:4px 0;color:#94a3b8;">')
            html = html.replace('<img ', '<img style="max-width:100%;height:auto;" ')
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





