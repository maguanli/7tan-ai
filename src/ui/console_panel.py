"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗
使用 OS 级管道重定向，捕获所有输出：
- Python print() / sys.stdout / sys.stderr
- loguru 日志
- subprocess 子进程输出
- C 扩展 / 浏览器引擎调试输出
- 任何写入 fd 1 和 fd 2 的内容

模块加载时立即安装重定向，确保不丢失任何启动输出。
"""
import os
import sys
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QScrollBar,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal

# ===== 本地颜色常量 =====
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
    """线程安全的日志信号，pipe reader 通过此信号将日志投递到主线程"""
    log_received = pyqtSignal(str)


_global_log_signal = _LogSignal()


# ===== OS 级管道重定向（捕获一切输出）=====
_orig_stdout_fd: int = -1
_orig_stderr_fd: int = -1
_pipe_read: int = -1
_pipe_write: int = -1
_reader_running = False


def _install_os_redirect():
    """
    OS 级重定向：用 os.dup2 将 fd 1 (stdout) 和 fd 2 (stderr)
    都指向管道写端。任何进程/子进程写入这两个 fd 的内容都会被捕获。
    后台线程持续从管道读端读取并发送到信号。
    """
    global _orig_stdout_fd, _orig_stderr_fd, _pipe_read, _pipe_write, _reader_running

    if _reader_running:
        return

    # 保存原始 fd（用于回写调试 + 必要时恢复）
    _orig_stdout_fd = os.dup(1)
    _orig_stderr_fd = os.dup(2)

    # 创建管道
    _pipe_read, _pipe_write = os.pipe()

    # 重定向 OS 级 stdout / stderr 到管道写端
    os.dup2(_pipe_write, 1)
    os.dup2(_pipe_write, 2)

    # 让 Python 的 sys.stdout / sys.stderr 变为行缓冲模式
    # （管道默认是块缓冲，行缓冲确保实时输出）
    sys.stdout = os.fdopen(os.dup(1), 'w', buffering=1, encoding='utf-8', errors='replace')
    sys.stderr = os.fdopen(os.dup(2), 'w', buffering=1, encoding='utf-8', errors='replace')

    # 后台线程：持续从管道读取并发送信号
    _reader_running = True

    def _pipe_reader():
        buf = b""
        while _reader_running:
            try:
                data = os.read(_pipe_read, 65536)
                if not data:
                    break

                # 回写到原始 stdout（便于外部调试，如从命令行启动时仍能看到输出）
                try:
                    os.write(_orig_stdout_fd, data)
                except Exception:
                    pass

                # 解析行并发送信号
                buf += data
                while b'\n' in buf:
                    raw_line, buf = buf.split(b'\n', 1)
                    text = raw_line.decode('utf-8', errors='replace').rstrip('\r')
                    if text:
                        ts = datetime.now().strftime("%H:%M:%S")
                        _global_log_signal.log_received.emit(f"{ts} │ {text}")
            except Exception:
                break

    t = threading.Thread(target=_pipe_reader, daemon=True, name="console-pipe-reader")
    t.start()


# 模块加载时立即安装 OS 级重定向
_install_os_redirect()


# ===== 控制台面板组件 =====
class ConsoleViewer(QWidget):
    """实时日志控制台 — 嵌入工作台左侧面板"""

    def __init__(self):
        super().__init__()
        T = CONSOLE_THEME

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

        # 行数显示
        self._line_count = QLabel("0 行")
        self._line_count.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 6px;"
        )
        bar.addWidget(self._line_count)

        layout.addLayout(bar)

        # --- 日志输出区 ---
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(10000)  # 比之前多一倍
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
        status = QLabel("💡 OS级管道重定向 — 捕获 stdout/stderr/subprocess/loguru 全部输出")
        status.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 4px;"
        )
        layout.addWidget(status)

        # 订阅全局日志信号
        _global_log_signal.log_received.connect(
            self._append_log, Qt.ConnectionType.QueuedConnection
        )

        self._total_lines = 0

    def _append_log(self, text: str):
        """追加一条日志（主线程安全）"""
        self._output.appendPlainText(text)
        self._total_lines += 1
        # 每 100 行更新一次计数
        if self._total_lines % 100 == 0:
            self._line_count.setText(f"{self._total_lines} 行")
        if self._auto_scroll:
            scrollbar = self._output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
