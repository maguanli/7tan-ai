"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗

三层捕获策略（从底层到高层）：
  第1层 — loguru sink：直接注册到 loguru，捕获所有 logger 输出
  第2层 — Python 级重定向：替换 sys.stdout / sys.stderr 为自定义对象
  第3层 — OS 管道重定向：os.dup2() 替换 fd 1/2（有 console 时生效）

确保无论 console=True/False，所有输出都能在面板中显示。
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


# ===== 全局日志队列（线程安全，纯 Python，不依赖 PyQt6）=====
_log_queue = queue.Queue(maxsize=20000)

# 用于去重的最后一行缓存
_last_line = None


def _enqueue(line: str):
    """将一行文本放入队列（线程安全），自动去重连续相同行"""
    global _last_line
    line = line.strip('\r\n')
    if not line:
        return
    clean = _strip_ansi(line)
    if not clean.strip():
        return
    # 去重：连续相同行只保留一条
    if clean == _last_line:
        return
    _last_line = clean
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        _log_queue.put_nowait(f"{ts} │ {clean}")
    except queue.Full:
        try:
            _log_queue.get_nowait()
            _log_queue.put_nowait(f"{ts} │ {clean}")
        except queue.Empty:
            pass


# ===== 第1层：loguru sink =====
def _install_loguru_sink():
    """注册 loguru 自定义 sink，捕获所有 logger 输出"""
    try:
        from loguru import logger
        # 移除默认的 stderr handler 避免双重输出
        logger.remove()
        # 添加文件 sink（保留原有日志文件功能）
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="DEBUG",
            colorize=False,
        )
        # 添加队列 sink
        logger.add(
            lambda msg: _enqueue(msg.record["message"].strip()),
            format="{message}",
            level="DEBUG",
            colorize=False,
        )
        _enqueue("[系统] ✅ loguru sink 已注册")
    except ImportError:
        _enqueue("[系统] ⚠️ loguru 未安装，跳过 sink 注册")
    except Exception as e:
        _enqueue(f"[系统] ⚠️ loguru sink 注册失败: {e}")


# ===== 第2层：Python 级 stdout/stderr 重定向 =====
class _StreamRedirector:
    """线程安全的类文件对象，write() 时按行放入队列"""

    def __init__(self):
        self._buf = ""
        self._lock = threading.Lock()

    def write(self, s: str):
        if not s:
            return
        with self._lock:
            self._buf += s
            while '\n' in self._buf:
                line, self._buf = self._buf.split('\n', 1)
                _enqueue(line)

    def flush(self):
        with self._lock:
            if self._buf:
                _enqueue(self._buf)
                self._buf = ""

    def isatty(self):
        return False


def _install_python_redirect():
    """替换 sys.stdout 和 sys.stderr"""
    redirector = _StreamRedirector()
    sys.stdout = redirector
    sys.stderr = redirector
    _enqueue("[系统] ✅ Python stdout/stderr 重定向已安装")


# ===== 第3层：OS 管道重定向（有 console 时生效）=====
_pipe_installed = False
_saved_stdout_fd = None
_saved_stderr_fd = None


def _install_os_pipe_redirect():
    """
    OS 级管道重定向。仅在 fd 1/2 有效时安装。
    如果 console=False（Windows GUI 模式），静默跳过。
    """
    global _pipe_installed, _saved_stdout_fd, _saved_stderr_fd
    if _pipe_installed:
        return
    _pipe_installed = True

    # 检查 fd 1 是否有效
    try:
        os.dup(1)
    except OSError:
        _enqueue("[系统] ⚠️ fd 1 无效（GUI 模式），跳过 OS 管道重定向")
        return

    try:
        _saved_stdout_fd = os.dup(1)
    except OSError:
        _saved_stdout_fd = None

    try:
        _saved_stderr_fd = os.dup(2)
    except OSError:
        _saved_stderr_fd = None

    pipe_read, pipe_write = os.pipe()
    os.dup2(pipe_write, 1)
    os.dup2(pipe_write, 2)

    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass

    def _pipe_reader():
        buf = b""
        while True:
            try:
                chunk = os.read(pipe_read, 8192)
                if not chunk:
                    break
                if _saved_stdout_fd is not None:
                    try:
                        os.write(_saved_stdout_fd, chunk)
                    except (OSError, ValueError):
                        pass
                buf += chunk
                while b'\n' in buf:
                    line_bytes, buf = buf.split(b'\n', 1)
                    line = line_bytes.decode('utf-8', errors='replace').rstrip('\r')
                    _enqueue(line)
            except (OSError, ValueError):
                break

    t = threading.Thread(target=_pipe_reader, daemon=True, name="pipe-reader")
    t.start()
    _enqueue("[系统] ✅ OS 管道重定向已安装")


# ===== 安装所有捕获层 =====
def install_all():
    """安装所有三层捕获（幂等，只执行一次）"""
    if getattr(install_all, '_done', False):
        return
    install_all._done = True

    # 第1层：loguru sink（必须在 Python 重定向前，否则 loguru 的 stderr 被替换）
    _install_loguru_sink()
    # 第2层：Python stdout/stderr
    _install_python_redirect()
    # 第3层：OS 管道
    _install_os_pipe_redirect()


# ⚡ 模块加载时立即安装
install_all()


# ===== 控制台面板 UI 组件 =====
class ConsoleViewer(QWidget):
    """实时日志控制台 — 三层全捕获"""

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
            QPushButton:hover {{ background: {T['accent']}44; }}
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

        # 行数标签
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
        status = QLabel("💡 三层捕获：loguru + Python stdout/stderr + OS 管道 — 与黑窗完全一致")
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
        while drained < 200:
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
        self._timer.stop()
        super().closeEvent(event)
