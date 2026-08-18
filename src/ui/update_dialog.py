"""
更新对话框 — 展示新版本信息 / 下载进度 / 应用更新

流程:
  检查到新版本 → UpdateDialog(latest) 弹出
    → 用户点 [下载更新] → POST /api/update/download → 轮询 /api/update/progress
    → 下载完成 → [立即重启更新] → POST /api/update/apply → 退出主程序（update.bat 接管）

线程说明:
  所有 requests 均在 QThread 中执行，避免阻塞 UI 主线程；
  服务端 apply 需解压更新包（可能>10s），超时放宽到 300s，避免误报"无法启动更新程序"。
"""
import os
import time

import requests
from loguru import logger
from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout,
)

from .theme import THEME

API_BASE = f"http://127.0.0.1:{os.environ.get('7TAN_PORT', '9800')}"


class _ApiThread(QThread):
    """后台执行 API 请求，避免阻塞 UI 主线程"""
    success = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, method: str, url: str, timeout: int = 120, parent=None):
        super().__init__(parent)
        self._method = method
        self._url = url
        self._timeout = timeout

    def run(self):
        try:
            resp = requests.request(self._method, self._url, timeout=self._timeout)
            resp.raise_for_status()
            self.success.emit(resp.json())
        except Exception as exc:
            logger.error(f"api request failed: {self._method} {self._url}: {exc}")
            self.failed.emit(str(exc))


def _fmt_size(n: int) -> str:
    if not n:
        return "未知大小"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class UpdateDialog(QDialog):
    """发现新版本对话框"""

    def __init__(self, latest: dict, parent=None):
        super().__init__(parent)
        self._latest = latest or {}
        self._task_id = ""
        self._downloading = False
        self._thread: _ApiThread | None = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll_progress)

        self.setWindowTitle("🔄 发现新版本")
        self.setMinimumWidth(460)
        self._build_ui()
        self.setStyleSheet(f"""
            QDialog {{ background: {THEME['bg_dark']}; }}
            QLabel {{ color: {THEME['text_primary']}; }}
            QLabel.muted {{ color: {THEME['text_secondary']}; }}
            QProgressBar {{
                background: {THEME['bg_input']}; border: 1px solid {THEME['border']};
                border-radius: 6px; height: 18px; text-align: center;
            }}
            QProgressBar::chunk {{ background: {THEME['accent']}; border-radius: 5px; }}
        """)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        info = self._latest
        ver = info.get("version", "?")
        notes = info.get("notes") or "本次更新包含功能优化与问题修复。"

        title = QLabel(f"✨ 新版本 v{ver} 可用")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['accent']};")
        lay.addWidget(title)

        cur = QLabel(f"当前版本: v{info.get('_current', '')}  →  最新版本: v{ver}")
        cur.setProperty("class", "muted")
        cur.setStyleSheet(f"font-size: 12px; color: {THEME['text_secondary']};")
        lay.addWidget(cur)

        meta = QLabel(
            f"大小: {_fmt_size(info.get('size', 0))}　|　发布时间: {info.get('release_date', '')}"
        )
        meta.setProperty("class", "muted")
        meta.setStyleSheet(f"font-size: 12px; color: {THEME['text_secondary']};")
        lay.addWidget(meta)

        # 更新说明
        notes_lbl = QLabel("📝 更新内容:")
        notes_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {THEME['text_primary']};")
        lay.addWidget(notes_lbl)

        self._notes = QLabel(notes)
        self._notes.setWordWrap(True)
        self._notes.setStyleSheet(
            f"background: {THEME['bg_input']}; border: 1px solid {THEME['border']};"
            f"border-radius: 8px; padding: 10px; font-size: 12px; color: {THEME['text_secondary']};"
        )
        lay.addWidget(self._notes)

        # 进度条
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("等待下载…")
        lay.addWidget(self._progress)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setStyleSheet(
            f"background: {THEME['bg_input']}; color: {THEME['text_primary']}; border: 1px solid {THEME['border']};"
        )
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        self._dl_btn = QPushButton("⬇️ 下载更新")
        self._dl_btn.setStyleSheet(f"background: {THEME['accent']}; color: #000;")
        self._dl_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._dl_btn)
        lay.addLayout(btn_row)

    # ============ 下载 ============
    def _start_download(self):
        self._downloading = True
        self._dl_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._progress.setFormat("正在连接更新服务器…")
        # 后台线程执行：服务端会先联网检查更新（最长 10s），同步等待会卡 UI
        self._thread = _ApiThread("POST", f"{API_BASE}/api/update/download", timeout=120, parent=self)
        self._thread.success.connect(self._on_download_started)
        self._thread.failed.connect(self._on_download_failed)
        self._thread.start()

    def _on_download_started(self, data: dict):
        self._task_id = data.get("task_id", "")
        if self._task_id:
            self._progress.setFormat("正在下载 0%")
            self._poll_timer.start()
        else:
            self._on_download_failed("服务器未返回下载任务 ID")

    def _on_download_failed(self, msg: str):
        self._downloading = False
        self._dl_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)
        self._progress.setFormat("等待下载…")
        QMessageBox.warning(self, "下载失败", f"无法开始下载:\n{msg}")

    def _poll_progress(self):
        if not self._task_id:
            return
        try:
            resp = requests.get(
                f"{API_BASE}/api/update/progress", params={"task_id": self._task_id}, timeout=10
            )
            resp.raise_for_status()
            st = resp.json()
        except Exception:
            return  # 网络抖动，下一轮再试

        status = st.get("status", "")
        done, total = st.get("done", 0), st.get("total", 0)
        if total:
            pct = int(done * 100 / total)
            self._progress.setValue(pct)
            self._progress.setFormat(f"正在下载 {pct}%  ({_fmt_size(done)} / {_fmt_size(total)})")

        if status == "done":
            self._poll_timer.stop()
            self._progress.setValue(100)
            self._progress.setFormat("✅ 下载完成")
            self._dl_btn.setText("🚀 立即重启更新")
            self._dl_btn.setEnabled(True)
            self._cancel_btn.setText("稍后再说")
            self._cancel_btn.setEnabled(True)
            self._dl_btn.clicked.disconnect()
            self._dl_btn.clicked.connect(self._apply)
        elif status == "error":
            self._poll_timer.stop()
            self._progress.setFormat("❌ 下载失败")
            self._dl_btn.setEnabled(True)
            self._cancel_btn.setEnabled(True)
            QMessageBox.warning(self, "下载失败", st.get("error", "未知错误"))

    # ============ 应用更新 ============
    def _apply(self):
        self._dl_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._progress.setFormat("正在启动更新程序，请稍候…")
        # 后台线程执行：服务端 apply 需解压更新包（可能>10s），
        # 超时给 300s，避免误报"无法启动更新程序"
        self._thread = _ApiThread("POST", f"{API_BASE}/api/update/apply", timeout=300, parent=self)
        self._thread.success.connect(self._on_apply_done)
        self._thread.failed.connect(self._on_apply_failed)
        self._thread.start()

    def _on_apply_done(self, data: dict):
        if not data.get("ok"):
            self._on_apply_failed(data.get("message", "未知错误"))
            return
        # 更新脚本已启动 → 退出主程序，由 update.bat 接管替换与重启
        QMessageBox.information(self, "更新中", "软件将在 5 秒后自动关闭并完成更新，请稍候…")
        try:
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception:
            import os
            os._exit(0)

    def _on_apply_failed(self, msg: str):
        self._dl_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)
        self._progress.setFormat("等待下载…")
        QMessageBox.warning(self, "更新失败", f"无法启动更新程序:\n{msg}")
