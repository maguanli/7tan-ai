"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗

多层捕获策略：
  1. loguru sink — 直接注册到 loguru，捕获所有 logger 输出
  2. Python 重定向 — 替换 sys.stdout / sys.stderr
  3. OS 管道 — os.dup2()（有 console 时生效）

修复记录 (2025-07-18):
  - P1-3: _log_queue 改为无界队列，避免队列满导致管道阻塞 → GUI 假死
  - P1-4: _install_os_pipe 去掉 os.write(saved_out) 回写，避免死循环
  - P2-5: install_all() 加文件锁防重入
  - P3-6: QPlainTextEdit → QTextEdit + insertHtml 语法高亮，不再逐行 appendPlainText
  - P4-7: _enqueue 加去重哈希环(最近200条)，消除三层捕获导致的2~3倍重复日志
  - P5-8: 简化高亮规则，去掉过度花哨的 CSS 边框/背景
"""
import os
import sys
import re
import html as _html_lib
import queue
import threading
import tempfile
from datetime import datetime
from collections import deque as _deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QScrollBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor, QFont

# ===== ANSI =====
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


# ===== 语法高亮规则 =====
_HIGHLIGHT_RULES: list[tuple[str, str]] = [
    (r'\b(ERROR|CRITICAL|FATAL|Traceback|❌|💥|🔴)\b', '#ef4444'),
    (r'\b(WARNING|WARN|⚠️|⚠|🟠)\b', '#f59e0b'),
    (r'\b(SUCCESS|✅|🟢|OK\b)', '#10b981'),
    (r'\b(INFO|ℹ️|🔵)\b', '#3b82f6'),
    (r'\b(DEBUG|🐛)\b', '#8b5cf6'),
    (r'\b(正在|开始|启动|🚀|⏳|🔄|📦|🔧)\b', '#00d4ff'),
    (r'\b(完成|成功|就绪|通过|正常|🎉)\b', '#10b981'),
    (r'\b(失败|错误|异常|超时|崩溃|拒绝|不可用)\b', '#ef4444'),
    (r'\bhttps?://\S+', '#60a5fa'),
    (r'\b[A-Za-z_]+\.py\b', '#fbbf24'),
    (r'\b(\d+\.\d+)\s*(GB|MB|KB|秒|s|ms|行|条)\b', '#fb923c'),
    (r'\b(True|False|None)\b', '#c084fc'),
]

_HIGHLIGHT_PATTERNS = [(re.compile(p), c) for p, c in _HIGHLIGHT_RULES]


def _highlight_line(text: str) -> str:
    """把一行纯文本转成带颜色 span 的 HTML"""
    escaped = _html_lib.escape(text, quote=False)
    result = escaped
    for pattern, color in _HIGHLIGHT_PATTERNS:
        result = pattern.sub(
            lambda m, c=color: f'<span style="color:{c};font-weight:bold;">{m.group(0)}</span>',
            result,
        )
    return result


# ===== 全局日志队列 =====
_log_queue = queue.Queue()
_dedup_ring: _deque = _deque(maxlen=200)


def _enqueue(line: str):
    line = line.strip('\r\n')
    if not line:
        return
    clean = _strip_ansi(line)
    if not clean.strip():
        return
    h = hash(clean)
    if h in _dedup_ring:
        return
    _dedup_ring.append(h)
    ts = datetime.now().strftime("%H:%M:%S")
    _log_queue.put(f"{ts} │ {clean}")


# ===== 1. loguru sink =====
_loguru_sink_id = None


def _add_loguru_sink():
    global _loguru_sink_id
    try:
        from loguru import logger
        if _loguru_sink_id is not None:
            try:
                logger.remove(_loguru_sink_id)
            except Exception:
                pass
        try:
            logger.remove(0)
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
        pass
    except Exception as e:
        _enqueue(f"[系统] loguru sink 失败: {e}")


# ===== 2. Python stdout/stderr 重定向 =====
class _StreamRedirector:
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
                buf += chunk
                while b'\n' in buf:
                    lb, buf = buf.split(b'\n', 1)
                    _enqueue(lb.decode('utf-8', errors='replace').rstrip('\r'))
            except Exception:
                break

    threading.Thread(target=_reader, daemon=True, name="pipe").start()
    _enqueue("[系统] OS 管道已安装")


_install_lock_path = os.path.join(tempfile.gettempdir(), f"7tan_console_install_{os.getpid()}.lock")


def install_all():
    if getattr(install_all, '_done', False):
        return
    if os.path.exists(_install_lock_path):
        return
    install_all._done = True
    try:
        with open(_install_lock_path, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    _install_python_redirect()
    _install_os_pipe()
    _add_loguru_sink()
    import atexit
    @atexit.register
    def _cleanup_lock():
        try:
            os.remove(_install_lock_path)
        except Exception:
            pass


install_all()


def refresh_loguru_sink():
    _add_loguru_sink()


# ===== UI：实时控制台 =====
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
    """实时日志控制台 — QTextEdit + insertHtml 高亮"""

    def __init__(self):
        super().__init__()
        T = CONSOLE_THEME

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── 顶部工具栏 ──
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
        clear_btn.clicked.connect(self._output.clear)
        bar.addWidget(clear_btn)

        self._line_count = QLabel("0 行")
        self._line_count.setStyleSheet(f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 6px;")
        bar.addWidget(self._line_count)
        layout.addLayout(bar)

        # ── 输出区：QTextEdit 替代 QPlainTextEdit，完整支持 HTML ──
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(f"""
            QTextEdit {{
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

        # ── 底部状态 ──
        status = QLabel("loguru + Python + OS 管道  |  语法高亮  |  去重")
        status.setStyleSheet(f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 4px;")
        layout.addWidget(status)

        self._total_lines = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start(50)

    def _drain_queue(self):
        """批量收集 → 一次性 insertHtml，避免频繁重绘"""
        lines = []
        while len(lines) < 200:
            try:
                line = _log_queue.get_nowait()
            except queue.Empty:
                break
            lines.append(line)

        if not lines:
            return

        self._total_lines += len(lines)
        self._line_count.setText(f"{self._total_lines} 行")

        # 构建 HTML，每行一个 <div>，高亮关键词
        html_parts = []
        for line in lines:
            highlighted = _highlight_line(line)
            html_parts.append(
                f'<div style="line-height:1.55;white-space:pre;'
                f'font-family:\'Cascadia Code\',\'Fira Code\',Consolas,monospace;'
                f'font-size:12px;">{highlighted}</div>'
            )

        batch_html = ''.join(html_parts)

        # 一次性插入
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(batch_html)

        if self._auto_scroll:
            sb = self._output.verticalScrollBar()
            sb.setValue(sb.maximum())

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
