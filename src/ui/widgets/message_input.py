"""Enter 发送输入框（增强版）— 从 chat_page 拆分"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPlainTextEdit
from ._theme import THEME


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
                super().keyPressEvent(event)
            else:
                text = self.toPlainText().strip()
                if text:
                    self.send_triggered.emit(text)
                    self.clear()
        else:
            super().keyPressEvent(event)
