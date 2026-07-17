"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗

多层捕获策略：
  1. loguru sink — 直接注册到 loguru，捕获所有 logger 输出
  2. Python 重定向 — 替换 sys.stdout / sys.stderr
  3. OS 管道 — os.dup2()（有 console 时生效）

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

# ===== ANSI =====
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


# ===== 全局日志队列 =====
_log_queue = queue.Queue(maxsize=20000)


def _enqueue(line: str):
    """将一行文本放入队列"""
    line = line.strip('\r\n')
    if not line:
        return
    clean = _strip_ansi(line)
    if not clean.strip():
        return
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        _log_queue.put_nowait(f"{ts} │ {clean}")
    except queue.Full:
        try:
            _log_queue.get_nowait()
            _log_queue.put_nowait(f"{ts} │ {clean}")
        except queue.Empty:
            pass


# ===== 1. loguru sink =====
_loguru_sink_id = None

def _add_loguru_sink():
    """添加 loguru 队列 sink（每次都重新注册，支持 setup_logging 后调用）"""
    global _loguru_sink_id
    try:
        from loguru import logger
        # 如果之前注册过，先移除旧的
        if _loguru_sink_id is not None:
            try:
                logger.remove(_loguru_sink_id)
            except Exception:
                pass
        _loguru_sink_id = logger.add(
            lambda msg: _enqueue(str(msg).strip()),
            format="{message}",
            level="DEBUG",
            colorize=False,
        )
        _enqueue("[系统] loguru 控制台 sink 已连接")
    except ImportError:
        pass  # loguru 还没安装，静默跳过
    except Exception as e:
        _enqueue(f"[系统] loguru sink 失败: {e}")


# ===== 2. Python stdout/stderr 重定向 =====
class _StreamRedirector:
    """线程安全的类文件对象"""

    def __init__(self):
        self._buf = ""
        self._lock = threading.Lock()

    def write(self, s):
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

    def fileno(self):
        """返回原始 stderr 的 fileno，兼容 loguru 等需要 fileno 的库"""
        try:
            return sys.__stderr__.fileno()
        except Exception:
            raise OSError("no fileno")


_redirector = None

def _install_python_redirect():
    global _redirector
    _redirector = _StreamRedirector()
    sys.stdout = _redirector
    sys.stderr = _redirector
    _enqueue("[系统] Python stdout/stderr 重定向已安装")


# ===== 3. OS 管道 =====
def _install_os_pipe():
    try:
        os.dup(1)
    except OSError:
        _enqueue("[系统] GUI 模式，跳过 OS 管道")
        return

    try:
        saved_out = os.dup(1)
    except OSError:
        saved_out = None
    try:
        saved_err = os.dup(2)
    except OSError:
        saved_err = None

    r, w = os.pipe()
    os.dup2(w, 1)
    os.dup2(w, 2)

    def _reader():
        buf = b""
        while True:
            try:
                chunk = os.read(r, 8192)
                if not chunk:
                    break
                if saved_out is not None:
                    try:
                        os.write(saved_out, chunk)
                    except Exception:
                        pass
                buf += chunk
                while b'\n' in buf:
                    lb, buf = buf.split(b'\n', 1)
                    _enqueue(lb.decode('utf-8', errors='replace').rstrip('\r'))
            except Exception:
                break

    threading.Thread(target=_reader, daemon=True, name="pipe").start()
    _enqueue("[系统] OS 管道已安装")


# ===== 安装 =====
def install_all():
    if getattr(install_all, '_done', False):
        return
    install_all._done = True
    _install_python_redirect()
    _install_os_pipe()
    _add_loguru_sink()


# ⚡ 模块加载时执行基础安装（loguru 可能还没导入，后面 setup_logging 会再次触发）
install_all()


# ===== 供外部调用：loguru 配置完成后重新注册 sink =====
def refresh_loguru_sink():
    """setup_logging() 之后调用，重新注册 loguru sink"""
    _add_loguru_sink()


# ===== UI =====
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


class ConsoleViewer(QWidget):
    """实时日志控制台"""

    def __init__(self):
        super().__init__()
        T = CONSOLE_THEME

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 工具栏
        bar = QHBoxLayout()
        title = QLabel("📟 实时控制台")
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {T['text_primary']};")
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
            QPushButton:hover {{ background: {T['accent']}44; }}
        """)
        self._auto_btn.clicked.connect(lambda: setattr(self, '_auto_scroll', self._auto_btn.isChecked()))
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

        self._line_count = QLabel("0 行")
        self._line_count.setStyleSheet(f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 6px;")
        bar.addWidget(self._line_count)
        layout.addLayout(bar)

        # 输出区
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

        status = QLabel("多层捕获：loguru + Python + OS管道")
        status.setStyleSheet(f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 4px;")
        layout.addWidget(status)

        self._total_lines = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start(50)

    def _drain_queue(self):
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
                sb = self._output.verticalScrollBar()
                sb.setValue(sb.maximum())

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
