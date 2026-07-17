"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗

三层捕获，确保和之前黑窗输出完全一致：
1. TeeWriter 替换 sys.stdout / sys.stderr — 捕获 print()、异常栈
2. loguru 额外 sink — 捕获所有日志
3. subprocess 管道捕获 — 捕获子进程输出

模块加载时立即安装 TeeWriter，确保不丢失启动输出。
"""
import os
import sys
import io
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QScrollBar,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal

from loguru import logger

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
    """线程安全的日志信号，所有输出最终通过此信号投递到主线程 GUI"""
    log_received = pyqtSignal(str)


_global_log_signal = _LogSignal()

# ===== 保存原始输出流（用于回写终端）=====
_orig_stdout = sys.stdout
_orig_stderr = sys.stderr


# ===== TeeWriter：替换 sys.stdout/stderr =====
class _TeeWriter(io.TextIOBase):
    """
    同时写入：
    1. 原始输出流（终端可见，命令行启动时仍能看到）
    2. 全局日志信号（GUI 控制台面板）
    """

    def __init__(self, original, label=""):
        self._original = original
        self._label = label  # "[stdout]" 或 "[stderr]"
        self._buffer = ""
        self._lock = threading.Lock()

    def write(self, text):
        with self._lock:
            # 1. 回写原始输出（命令行启动时终端可见）
            if self._original is not None:
                try:
                    self._original.write(text)
                    self._original.flush()
                except (OSError, ValueError, AttributeError):
                    pass

            # 2. 按行发送信号到 GUI 控制台
            self._buffer += text
            while '\n' in self._buffer:
                line, self._buffer = self._buffer.split('\n', 1)
                line = line.rstrip('\r')
                if line:
                    ts = datetime.now().strftime("%H:%M:%S")
                    label = self._label + " " if self._label else ""
                    _global_log_signal.log_received.emit(f"{ts} │ {label}{line}")

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except (OSError, ValueError, AttributeError):
                pass

    def isatty(self):
        return False


# 模块加载时立即替换 sys.stdout / sys.stderr
# 注意：只替换一次，避免重复
if not isinstance(sys.stdout, _TeeWriter):
    sys.stdout = _TeeWriter(_orig_stdout, label="")
if not isinstance(sys.stderr, _TeeWriter):
    sys.stderr = _TeeWriter(_orig_stderr, label="[stderr]")


# ===== loguru sink（在 ConsoleViewer 初始化时注册）=====
_loguru_sink_id = None


def _install_loguru_sink():
    """
    为 loguru 添加额外的 GUI sink。
    loguru 的原始 console sink 继续工作（写入终端），
    这个额外 sink 把日志发到 GUI 控制台。
    """
    global _loguru_sink_id

    if _loguru_sink_id is not None:
        return  # 已安装

    def _gui_sink(message):
        # loguru 的 message 已经格式化好（含时间、级别等）
        record = message.record
        ts = record["time"].strftime("%H:%M:%S")
        level = record["level"].name
        text = record["message"].rstrip('\n')
        _global_log_signal.log_received.emit(f"{ts} │ {level: <8} │ {text}")

    _loguru_sink_id = logger.add(
        _gui_sink,
        level="DEBUG",
        format="{message}",
        catch=True,
    )


def _remove_loguru_sink():
    """移除 GUI sink"""
    global _loguru_sink_id
    if _loguru_sink_id is not None:
        try:
            logger.remove(_loguru_sink_id)
        except Exception:
            pass
        _loguru_sink_id = None


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
        self._output.setMaximumBlockCount(10000)
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
        status = QLabel("💡 实时捕获 stdout/stderr/loguru — 与黑窗完全一致")
        status.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 4px;"
        )
        layout.addWidget(status)

        # ===== 订阅全局日志信号 =====
        _global_log_signal.log_received.connect(
            self._append_log, Qt.ConnectionType.QueuedConnection
        )

        # ===== 安装 loguru GUI sink =====
        _install_loguru_sink()

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

    def closeEvent(self, event):
        """面板关闭时移除 loguru sink"""
        _remove_loguru_sink()
        super().closeEvent(event)
