"""消息气泡组件 — 从 chat_page 拆分"""

import json
from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor, QTextOption
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QDialog, QMessageBox, QApplication,
    QSizePolicy, QTextBrowser,
)

# pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from ._theme import THEME


# ── 批量高度同步（性能优化，防主线程卡顿光标转圈）──────────────────
# 历史会话批量渲染时，若每条消息都用 QTimer.singleShot(0) 同步高度，
# 会形成 0ms 定时器风暴：全部在事件循环里连发，每个都触发 QTextDocument
# 全量布局（doc.size()），主线程被长时间占满 → 界面假死、光标变圈圈。
# 改为：合并到单个 60ms 定时器批次，逐条处理并在每条之间让出事件循环。
_pending_height_sync: list = []


def _drain_height_sync():
    """逐个处理待同步的气泡；每条之间让出事件循环，保证界面可响应。"""
    global _pending_height_sync
    if not _pending_height_sync:
        return
    bubble = _pending_height_sync.pop(0)
    try:
        bubble._sync_content_height()
    except Exception:
        pass  # 气泡可能已被删除（RuntimeError），忽略
    if _pending_height_sync:
        QTimer.singleShot(0, _drain_height_sync)  # 处理下一条前让事件循环喘息


class MessageBubble(QFrame):
    """单条消息的气泡组件，支持 Markdown、复制、重试"""

    retry_requested = pyqtSignal(str)  # 触发重试

    @classmethod
    def _schedule_height_sync(cls, bubble):
        """延迟批量同步气泡高度（合并 0ms 定时器风暴，防主线程卡顿光标转圈）。"""
        global _pending_height_sync
        _pending_height_sync.append(bubble)
        if len(_pending_height_sync) == 1:
            QTimer.singleShot(60, _drain_height_sync)  # 合并窗口：60ms 内入队的全部合并

    @staticmethod
    def _format_timestamp(ts: str) -> str:
        """统一时间显示：任意格式 → 'YYYY-MM-DD HH:MM'（含年月日）

        支持: 2026-08-03 13:45:22 / 2026-08-03T13:45:22.123456 / 13:45:22（纯时间补今天日期）
        """
        if not ts:
            return ""
        s = ts.strip()
        try:
            # 完整日期时间 → 截取 YYYY-MM-DD HH:MM
            if len(s) >= 16 and s[4] == '-' and s[7] == '-':
                return s[:16].replace('T', ' ')
            # 纯时间 HH:MM:SS / HH:MM → 补今天日期
            if len(s) >= 5 and s[2] == ':':
                from datetime import datetime
                return datetime.now().strftime("%Y-%m-%d") + " " + s[:5]
        except Exception:
            pass
        return s[:16]

    def __init__(self, role: str, content: str, timestamp: str = "",
                 cost: float = 0, iterations: int = 0, tokens: int = 0,
                 tool_calls: list = None, is_streaming: bool = False,
                 session_id: str = None, pre_parsed_html: str = None,
                 model_name: str = "", parent=None):
        super().__init__(parent)
        logger.debug(f"[MessageBubble] init start role={role} len={len(content)}")
        self._role = role
        self._content = content
        self._session_id = session_id
        self._is_streaming = is_streaming
        self._model_badge = None  # 模型名徽章引用（流式完成后可更新）

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ---- 头部：角色 + 时间戳 ----
        header = QHBoxLayout()
        header.setSpacing(8)
        self._header = header

        role_icon = {"user": "🧑", "assistant": "🤖", "system": "⚙️", "error": "❌",
                     "tool_call": "🔧", "tool_result": "📎"}.get(role, "💬")
        role_name = {"user": "你", "assistant": "AI", "system": "系统",
                     "error": "错误", "tool_call": "工具调用",
                     "tool_result": "结果"}.get(role, role)

        icon_label = QLabel(role_icon)
        icon_label.setFixedWidth(24)
        icon_label.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        header.addWidget(icon_label)

        role_label = QLabel(role_name)
        role_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {THEME['text_secondary']}; border: none; background: transparent;")
        header.addWidget(role_label)

        # 🤖 模型徽章：标明这条 AI 回复是哪个模型说的
        if role == "assistant" and model_name:
            model_badge = QLabel(model_name)
            model_badge.setStyleSheet(f"""
                QLabel {{
                    background: {THEME['accent']}22;
                    color: {THEME['accent']};
                    border: 1px solid {THEME['accent']}55;
                    border-radius: 8px;
                    padding: 1px 8px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
            self._model_badge = model_badge
            header.addWidget(model_badge)

        if timestamp:
            ts_label = QLabel(self._format_timestamp(timestamp))
            ts_label.setStyleSheet(f"font-size: 10px; color: {THEME['text_muted']}; border: none; background: transparent;")
            header.addWidget(ts_label)

        header.addStretch()

        # Token / 费用徽章（优先显示 Token 数）
        if tokens > 0 and role == "assistant":
            cost_badge = QLabel(f"🪙 {tokens:,} tokens")
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
        elif cost > 0 and role == "assistant":
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
        self._content_label = QTextBrowser()
        self._content_label.setReadOnly(True)
        self._content_label.setFrameShape(QFrame.Shape.NoFrame)
        self._content_label.setOpenExternalLinks(True)
        self._content_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content_label.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self._content_label.setStyleSheet("QTextBrowser { border: none; background: transparent; }")
        self._content_label.viewport().setAutoFillBackground(False)
        self._content_label.document().setDocumentMargin(0)
        # 高度自适应：内容/宽度变化时同步高度 = 文档实际高度（修复富文本显示不全）
        # [性能修复] 已移除 contentsChanged 连接：setHtml 时反复触发 QTextDocument 全量重排，
        # 是历史会话加载主线程卡顿(光标转圈)的根因，改为 setHtml 后一次性同步高度

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

        self._content_label.setHtml(html)
        MessageBubble._schedule_height_sync(self)  # 批量分片同步高度（替代 0ms 定时器风暴，防主线程卡顿光标转圈）
        logger.debug("[MessageBubble] setText done")

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
            html = html.replace('<table>', '<table style="border-collapse:collapse;width:100%;">')
            html = html.replace('<th>', '<th style="border:1px solid #334155;padding:6px;background:#1e293b;">')
            html = html.replace('<td>', '<td style="border:1px solid #334155;padding:6px;">')
            html = html.replace('<hr>', '<hr style="border-color:#334155;">')
            html = html.replace('<blockquote>', '<blockquote style="border-left:3px solid #334155;padding-left:12px;margin:8px 0;color:#94a3b8;">')
            html = html.replace('<img ', '<img style="max-width:100%;border-radius:6px;" ')
            if text_color:
                return f'<div style="color:{text_color};font-size:13px;line-height:1.6;word-break:break-word;overflow-wrap:break-word;max-width:100%;">{html}</div>'
            return f'<div style="color:{THEME["text_primary"]};font-size:13px;line-height:1.6;word-break:break-word;overflow-wrap:break-word;max-width:100%;">{html}</div>'
        except ImportError:
            esc = md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if text_color:
                return f'<div style="color:{text_color};font-size:13px;line-height:1.6;white-space:pre-wrap;max-width:100%;">{esc}</div>'
            return f'<div style="color:{THEME["text_primary"]};font-size:13px;line-height:1.6;white-space:pre-wrap;max-width:100%;">{esc}</div>'

    @staticmethod
    def _pygments_static(html: str) -> str:
        """Pygments 语法高亮（静态版本，线程安全）"""
        import re as _re
        def _highlight_code(m):
            code = m.group(2)
            lang = m.group(1) or ""
            try:
                lexer = get_lexer_by_name(lang, stripall=True) if lang else TextLexer()
            except ClassNotFound:
                lexer = TextLexer()
            formatter = HtmlFormatter(style='monokai', noclasses=True)
            highlighted = highlight(code, lexer, formatter)
            return f'<div style="background:#272822;border-radius:8px;padding:12px;margin:8px 0;overflow-x:auto;">{highlighted}</div>'
        return _re.sub(r'<pre><code(?: class="language-([^"]*)")?>(.*?)</code></pre>',
                       _highlight_code, html, flags=_re.DOTALL)

    def _pygments_highlight(self, html: str) -> str:
        """实例方法包装，捕获异常"""
        try:
            return self._pygments_static(html)
        except Exception as e:
            logger.warning(f"[MessageBubble] pygments failed: {e}")
            return html

    def _build_tool_call_widget(self, tc: dict) -> QFrame:
        """构建工具调用步骤的小部件"""
        w = QFrame()
        w.setStyleSheet(f"background:{THEME['bg_card']};border:1px solid {THEME['border']};border-radius:6px;padding:4px 8px;")
        wl = QVBoxLayout(w)
        wl.setContentsMargins(4, 2, 4, 2)
        wl.setSpacing(2)

        # top row: icon + tool name + toggle
        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        status_icon = {"running": "🔄", "success": "✅", "failed": "❌"}.get(tc.get("status", ""), "🔧")
        icon_lbl = QLabel(status_icon)
        icon_lbl.setStyleSheet("font-size:12px;border:none;background:transparent;")
        top_row.addWidget(icon_lbl)

        name_lbl = QLabel(f'<span style="color:{THEME["accent"]};font-weight:bold;">{tc.get("tool", "unknown")}</span>')
        name_lbl.setStyleSheet("border:none;background:transparent;font-size:11px;")
        top_row.addWidget(name_lbl)

        top_row.addStretch()

        toggle_btn = QPushButton("-")
        toggle_btn.setFixedSize(18, 18)
        toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {THEME['text_muted']};
                border: none; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ color: {THEME['accent']}; }}
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
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        cancel_btn.setStyleSheet(f"background:transparent;color:{THEME['text_secondary']};padding:6px 14px;border-radius:4px;border:1px solid {THEME['border']};")
        br.addWidget(cancel_btn)
        br.addStretch()
        sv = QPushButton("保存")
        def do_save():
            self._content = ed.toPlainText()
            self.update_content(self._content)
            dlg.accept()
        sv.clicked.connect(do_save)
        sv.setStyleSheet(f"background:{THEME['accent']};color:#fff;padding:6px 14px;border-radius:4px;")
        br.addWidget(sv)
        ly.addLayout(br)
        dlg.exec()

    def _delete_self(self):
        """删除自己的气泡（带确认）"""
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这条消息吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.setVisible(False)
            self.deleteLater()

    def set_tokens(self, tokens: int):
        """动态设置 Token 徽章（流式完成后调用，更新右上角显示）"""
        if tokens <= 0 or self._role != "assistant":
            return
        badge_style = f"""
            QLabel {{
                background: {THEME['accent2']}44;
                color: {THEME['accent2']};
                border: 1px solid {THEME['accent2']}66;
                border-radius: 8px;
                padding: 1px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
        """
        # 已有 Token 徽章 → 只更新文本
        for i in range(self._header.count()):
            w = self._header.itemAt(i).widget()
            if isinstance(w, QLabel) and "tokens" in w.text():
                w.setText(f"🪙 {tokens:,} tokens")
                return
        # 没有 → 新建徽章（放在迭代徽章之前）
        badge = QLabel(f"🪙 {tokens:,} tokens")
        badge.setStyleSheet(badge_style)
        insert_pos = self._header.count()
        for i in range(self._header.count()):
            w = self._header.itemAt(i).widget()
            if isinstance(w, QLabel) and w.text().startswith("🔄"):
                insert_pos = i
                break
        self._header.insertWidget(insert_pos, badge)

    def set_model_name(self, model_name: str):
        """设置/更新模型名徽章（流式完成后调用）"""
        if not model_name or self._role != "assistant":
            return
        if self._model_badge:
            # 已有徽章 → 更新文本
            self._model_badge.setText(model_name)
            self._model_badge.show()
        else:
            # 没有 → 新建徽章，插入到角色名后面（index=2: icon + role_label 之后）
            badge = QLabel(model_name)
            badge.setStyleSheet(f"""
                QLabel {{
                    background: {THEME['accent']}22;
                    color: {THEME['accent']};
                    border: 1px solid {THEME['accent']}55;
                    border-radius: 8px;
                    padding: 1px 8px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
            self._model_badge = badge
            self._header.insertWidget(2, badge)

    def _sync_content_height(self):
        """同步 QTextBrowser 高度 = 文档实际渲染高度，防止内容被裁剪（修复显示不全）"""
        try:
            tb = self._content_label
            doc = tb.document()
            w = tb.viewport().width()
            if w > 10 and abs(doc.textWidth() - w) > 1:
                doc.setTextWidth(w)
            h = doc.size().height()
            if h > 10:
                last = getattr(self, '_last_sync_h', 0)
                if abs(int(h) - last) > 1:
                    tb.setFixedHeight(int(h) + 4)
                    self._last_sync_h = int(h)
        except Exception:
            pass

    def resizeEvent(self, event):
        """窗口/气泡尺寸变化时重新同步内容高度"""
        super().resizeEvent(event)
        self._sync_content_height()

    def showEvent(self, event):
        """首次显示时同步内容高度"""
        super().showEvent(event)
        self._sync_content_height()

    def update_content(self, new_content: str, is_streaming: bool = False):
        """更新消息内容（流式模式会自动节流）"""
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
            # 非流式：清除流式残留 pending，确保渲染最新内容（修复显示不全）
            if hasattr(self, '_update_timer'):
                self._update_timer.stop()
                self._pending_content = new_content
            self._do_update_label()

    def _do_update_label(self):
        """实际执行 QLabel.setText
        
        流式模式下跳过 Markdown 解析（O(n²) 性能瓶颈），
        只做简单 HTML 转义 + 换行，流式结束后再完整渲染。
        """
        # 流式：用最近一次 pending 文本；非流式：始终用最新 _content（修复显示不全）
        if self._is_streaming:
            content = getattr(self, '_pending_content', self._content)
        else:
            content = self._content
        if self._is_streaming:
            # 快速路径：纯文本转义 + 换行，不解析 Markdown
            esc = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            esc = esc.replace('\n', '<br>')
            text_color = "#000000" if self._role == "user" else None
            color_style = f'color:{text_color};' if text_color else ''
            self._content_label.setHtml(
                f'<div style="{color_style}font-size:13px;line-height:1.6;word-break:break-word;">{esc}</div>'
            )
        else:
            self._content_label.setHtml(self._md_to_html(content, "#000000" if self._role == "user" else None))
