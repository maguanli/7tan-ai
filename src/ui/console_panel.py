"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗

OS 级管道重定向：使用 os.pipe() + os.dup2() 在操作系统层面捕获所有输出。
包括 print()、loguru、C 扩展、subprocess 子进程等，和黑窗完全一致。

架构：
  所有输出 → fd 1/2 → OS 管道 → 后台线程读取
                              ├→ 回写原始 fd（终端可见）
                              └→ queue.Queue → GUI ConsoleViewer（QTimer 消费）
"""
import os
import sys
import re
import queue
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QScrollBar,
)
from PyQt6.QtCore import Qt, QTimer

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

# ===== ANSI 转义码剥离 =====
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def _strip_ansi(text: str) -> str:
    """移除 ANSI 颜色/控制码"""
    return _ANSI_RE.sub('', text)

# ===== 全局日志队列（线程安全，不依赖 PyQt6）=====
_log_queue = queue.Queue(maxsize=20000)

# ===== OS 级管道重定向 =====
_pipe_installed = False
_saved_stdout_fd = None
_saved_stderr_fd = None

def _install_os_pipe_redirect():
    """
    OS 级管道重定向：使用 os.dup2() 将 fd 1 (stdout) 和 fd 2 (stderr)
    重定向到管道写端。后台线程持续读取管道，按行放入队列。

    此函数只执行一次，在模块加载时自动调用。
    """
    global _pipe_installed, _saved_stdout_fd, _saved_stderr_fd
    if _pipe_installed:
        return
    _pipe_installed = True

    # 1. 保存原始 fd（用于回写终端）
    try:
        _saved_stdout_fd = os.dup(1)
    except OSError:
        _saved_stdout_fd = None
    try:
        _saved_stderr_fd = os.dup(2)
    except OSError:
        _saved_stderr_fd = None

    # 2. 创建管道
    pipe_read, pipe_write = os.pipe()

    # 3. 重定向 fd 1 和 fd 2 → 管道写端
    os.dup2(pipe_write, 1)
    os.dup2(pipe_write, 2)

    # 4. 刷新 Python 缓冲 → 确保已缓冲的内容写入管道
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass

    # 5. 调整 Python 层为行缓冲（减少延迟）
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    # 6. 后台线程：持续读取管道 → 回写终端 + 放入队列
    def _pipe_reader():
        buf = b""
        while True:
            try:
                chunk = os.read(pipe_read, 8192)
                if not chunk:
                    break  # 管道关闭

                # 回写到原始终端（命令行启动时可见）
                if _saved_stdout_fd is not None:
                    try:
                        os.write(_saved_stdout_fd, chunk)
                    except (OSError, ValueError):
                        pass

                # 按行解析 → 放入队列
                buf += chunk
                while b'\n' in buf:
                    line_bytes, buf = buf.split(b'\n', 1)
                    line = line_bytes.decode('utf-8', errors='replace').rstrip('\r')
                    # 剥离 ANSI 码
                    clean = _strip_ansi(line)
                    if clean.strip():
                        ts = datetime.now().strftime("%H:%M:%S")
                        try:
                            _log_queue.put_nowait(f"{ts} │ {clean}")
                        except queue.Full:
                            # 队列满了就丢弃最旧的
                            try:
                                _log_queue.get_nowait()
                                _log_queue.put_nowait(f"{ts} │ {clean}")
                            except queue.Empty:
                                pass
            except (OSError, ValueError):
                break

    t = threading.Thread(target=_pipe_reader, daemon=True, name="console-pipe-reader")
    t.start()


# ⚡ 模块加载时立即执行管道重定向
_install_os_pipe_redirect()


# ===== 控制台面板组件 =====
class ConsoleViewer(QWidget):
    """实时日志控制台 — OS 级全捕获"""

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

        # 自动滚动按钮
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

        # 清空按钮
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

        # 行数
        self._line_count = QLabel("0 行")
        self._line_count.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 6px;"
        )
        bar.addWidget(self._line_count)

        layout.addLayout(bar)

        # --- 日志输出区（GitHub Dark 风格）---
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
        status = QLabel("💡 OS 级管道捕获 stdout/stderr — 与黑窗完全一致")
        status.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 4px;"
        )
        layout.addWidget(status)

        # ===== QTimer 消费队列（每 50ms 从队列取日志）=====
        self._total_lines = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start(50)

    def _drain_queue(self):
        """从队列取出日志并显示（主线程安全）"""
        drained = 0
        while drained < 200:  # 每次最多取 200 条，避免卡 UI
            try:
                line = _log_queue.get_nowait()
            except queue.Empty:
                break
            self._output.appendPlainText(line)
            self._total_lines += 1
            drained += 1

        if drained > 0:
            self._line_count.setText(f"{self._total_lines} 行")
            if self._auto_scroll:
                scrollbar = self._output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """面板关闭时停止定时器"""
        self._timer.stop()
        super().closeEvent(event)
