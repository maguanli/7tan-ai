"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗
所有 7Tan 工作日志实时显示在此面板中
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QScrollBar,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal

# 本地颜色常量（独立于 app.py，避免循环导入）
CONSOLE_THEME = {
    "accent": "#00d4ff",
    "accent2": "#7c3aed",
    "danger": "#ef4444",
    "text_primary": "#e2e8f0",
    "text_secondary": "#94a3b8",
    "border": "#1e293b",
    "bg_dark": "#1a1a2e",
    "bg_input": "#1e1e3a",
}


# ===== 全局日志信号（线程安全）=====
class _LogSignal(QObject):
    """线程安全的日志信号，loguru sink 通过此信号将日志投递到主线程"""
    log_received = pyqtSignal(str)


_global_log_signal = _LogSignal()


def _setup_console_log_sink():
    """注册 loguru sink，将所有日志实时推送到控制台面板"""
    try:
        from loguru import logger
        if not hasattr(_setup_console_log_sink, '_installed'):
            _setup_console_log_sink._installed = True

            def _sink(msg):
                try:
                    stripped = msg.rstrip('\n')
                    if stripped:
                        _global_log_signal.log_received.emit(stripped)
                except Exception:
                    pass

            logger.add(
                _sink,
                format="{time:HH:mm:ss} | {level: <8} | {message}",
                level="DEBUG",
                colorize=False,
                enqueue=True,
            )
    except ImportError:
        pass


class ConsoleViewer(QWidget):
    """实时日志控制台 — 嵌入工作台左侧面板"""

    def __init__(self):
        super().__init__()
        T = CONSOLE_THEME  # 简写

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- 工具栏 ---
        bar = QHBoxLayout()
        title = QLabel("📟 实时控制台")
        title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {T['text_primary']};"
        )
        bar.addWidget(title)
        bar.addStretch()

        self._auto_scroll = True
        self._auto_btn = QPushButton("🔽 自动滚动")
        self._auto_btn.setCheckable(True)
        self._auto_btn.setChecked(True)
        self._auto_btn.setFixedHeight(26)
        self._auto_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['accent']}33; color: {T['accent']};
                border: 1px solid {T['accent']}66; border-radius: 4px;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:checked {{ background: {T['accent']}66; }}
        """)
        self._auto_btn.clicked.connect(
            lambda: setattr(self, '_auto_scroll', self._auto_btn.isChecked())
        )
        bar.addWidget(self._auto_btn)

        clear_btn = QPushButton("🗑 清空")
        clear_btn.setFixedHeight(26)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['danger']}22; color: {T['danger']};
                border: 1px solid {T['danger']}44; border-radius: 4px;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {T['danger']}44; }}
        """)
        clear_btn.clicked.connect(lambda: self._output.clear())
        bar.addWidget(clear_btn)

        layout.addLayout(bar)

        # --- 日志输出区 ---
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(5000)  # 最多保留 5000 行
        self._output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #0D1117;
                color: #C9D1D9;
                border: 1px solid {T['border']};
                border-radius: 6px;
                font-family: "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
                selection-background-color: #264F78;
            }}
        """)
        layout.addWidget(self._output, 1)

        # --- 底部状态 ---
        status = QLabel("💡 此处实时显示 7Tan 的所有工作日志，等同于命令行黑窗输出")
        status.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 4px;"
        )
        layout.addWidget(status)

        # 订阅全局日志信号（QueuedConnection 确保主线程安全）
        _global_log_signal.log_received.connect(
            self._append_log, Qt.ConnectionType.QueuedConnection
        )

        # 首次实例化时注册 loguru sink
        _setup_console_log_sink()

    def _append_log(self, text: str):
        """追加一条日志（主线程安全）"""
        self._output.appendPlainText(text)
        if self._auto_scroll:
            scrollbar = self._output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
