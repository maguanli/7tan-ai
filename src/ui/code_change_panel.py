"""
实时变更面板 — 展示 AI 修改代码的实时 diff（方案 B）

功能：
  - 左侧：修改记录列表（时间 + 操作 + 文件），最新置顶
  - 右侧：diff 高亮视图（+绿 / -红 / @@蓝 / ---+++紫）
  - 📌 自动打开开关：AI 修改代码时自动弹出面板并置顶（默认开启）
  - 🗑 清空历史记录
  - QTimer 轮询 code_change_bus（线程安全队列，与日志控制台同模式）
"""
from __future__ import annotations

import html as _html
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QListWidget, QListWidgetItem, QSplitter,
)
from PyQt6.QtCore import Qt, QTimer, QByteArray

_GEOMETRY_FILE = Path("data/panel_geometry.json")

from ..utils.code_change_bus import drain_changes, load_history

CHANGE_THEME = {
    "accent": "#7c3aed",
    "accent2": "#00d4ff",
    "danger": "#ef4444",
    "ok": "#10b981",
    "text_primary": "#e2e8f0",
    "text_secondary": "#94a3b8",
    "border": "#1e293b",
    "bg": "#0D1117",
}

_ACTION_ICONS = {
    "write": "✏️",
    "replace": "🔧",
    "create": "🆕",
    "delete": "🗑️",
    "config": "⚙️",
}

_ACTION_LABELS = {
    "write": "重写",
    "replace": "替换",
    "create": "新建",
    "delete": "删除",
    "config": "配置",
}


def _action_icon(action: str) -> str:
    return _ACTION_ICONS.get(action, "📄")


def _action_label(action: str) -> str:
    return _ACTION_LABELS.get(action, action)


def _diff_to_html(diff_text: str) -> str:
    """diff 文本 → 行级高亮 HTML"""
    if not diff_text:
        return '<div style="color:#94a3b8;">（无差异内容）</div>'
    parts = []
    for line in diff_text.splitlines():
        esc = _html.escape(line)
        style = ""
        if line.startswith("+++") or line.startswith("---"):
            style = "color:#c084fc;font-weight:bold;"
        elif line.startswith("@@"):
            style = "color:#60a5fa;font-weight:bold;"
        elif line.startswith("+"):
            style = "color:#4ade80;background:#10b9811a;"
        elif line.startswith("-"):
            style = "color:#f87171;background:#ef44441a;"
        parts.append(
            f'<div style="{style}white-space:pre-wrap;font-family:\'Cascadia Code\',\'Fira Code\',Consolas,monospace;font-size:12px;line-height:1.5;">{esc}</div>'
        )
    return "".join(parts)


class CodeChangePanel(QWidget):
    """代码修改实时面板（独立窗口，可由控制台按钮打开 / AI 修改时自动打开）"""

    def __init__(self, parent=None, auto_open: bool = True):
        super().__init__(parent)
        self.setWindowTitle("🔧 代码修改实时")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self._auto_open = auto_open
        self._restore_geometry()
        self._records: list[dict] = []
        self._build_ui()
        self._load_history_records()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(60)

    # ── UI ──
    def _build_ui(self):
        T = CHANGE_THEME
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # ── 顶部工具栏 ──
        bar = QHBoxLayout()
        title = QLabel("🔧 代码修改实时")
        title.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{T['text_primary']};")
        bar.addWidget(title)

        self._count_label = QLabel("0 条")
        self._count_label.setStyleSheet(
            f"color:{T['text_secondary']};font-size:11px;padding:0 6px;")
        bar.addWidget(self._count_label)
        bar.addStretch()

        self._auto_btn = QPushButton("📌 自动打开")
        self._auto_btn.setCheckable(True)
        self._auto_btn.setChecked(self._auto_open)
        self._auto_btn.setFixedHeight(26)
        self._auto_btn.setToolTip("AI 修改代码时自动打开本面板")
        self._auto_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['ok']}22; color: {T['ok']};
                border: 1px solid {T['ok']}55; border-radius: 4px;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:checked {{ background: {T['ok']}55; }}
            QPushButton:hover {{ background: {T['ok']}33; }}
        """)
        self._auto_btn.clicked.connect(
            lambda: setattr(self, '_auto_open', self._auto_btn.isChecked()))
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
        clear_btn.clicked.connect(self._clear)
        bar.addWidget(clear_btn)

        close_btn = QPushButton("✖ 关闭")
        close_btn.setFixedHeight(26)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['accent']}33; color: {T['text_primary']};
                border: 1px solid {T['border']}; border-radius: 4px;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {T['accent']}55; }}
        """)
        close_btn.clicked.connect(self.hide)
        bar.addWidget(close_btn)
        layout.addLayout(bar)

        # ── 中部：左记录列表 + 右 diff 视图 ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {T['bg']}; color: #C9D1D9;
                border: 1px solid {T['border']}; border-radius: 6px;
                font-size: 11px; padding: 4px;
            }}
            QListWidget::item {{ padding: 5px 6px; border-bottom: 1px solid #161b22; }}
            QListWidget::item:selected {{ background: {T['accent']}44; }}
        """)
        self._list.currentRowChanged.connect(self._show_record)
        splitter.addWidget(self._list)

        self._diff_view = QTextEdit()
        self._diff_view.setReadOnly(True)
        self._diff_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._diff_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T['bg']}; color: #C9D1D9;
                border: 1px solid {T['border']}; border-radius: 6px;
                font-family: "Cascadia Code","Fira Code",Consolas,"Courier New",monospace;
                font-size: 12px; padding: 8px;
                selection-background-color: #264F78;
            }}
        """)
        splitter.addWidget(self._diff_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 620])
        layout.addWidget(splitter, 1)

        # ── 底部状态 ──
        self._status = QLabel("等待 AI 修改代码…")
        self._status.setStyleSheet(
            f"color:{T['text_secondary']};font-size:11px;padding:2px 4px;")
        layout.addWidget(self._status)

    # ── 历史加载（重启后不丢失）──
    def _load_history_records(self):
        """打开面板时加载持久化历史记录（最新在前），并清空队列中已持久化的重复项"""
        # 队列中的事件已同步写入历史文件，直接丢弃避免重复
        try:
            drain_changes(1000)
        except Exception:
            pass
        recs = load_history(300)
        seen = set()
        for rec in reversed(recs):  # 最新在前
            key = (rec.get("ts_full", ""), rec.get("action", ""), rec.get("path", ""))
            if key in seen:
                continue
            seen.add(key)
            self._records.append(rec)
            item = QListWidgetItem(
                f"[{rec.get('ts', '')}] {_action_icon(rec.get('action', ''))} {_action_label(rec.get('action', ''))}  {rec.get('path', '')}")
            item.setToolTip(rec.get("ts_full", ""))
            self._list.addItem(item)
        if self._records:
            self._list.setCurrentRow(0)
            self._show_record(0)
            self._count_label.setText(f"{len(self._records)} 条")
            last = self._records[0]
            self._status.setText(
                f"最新: {last.get('ts_full', '')}  {last.get('action', '')}  {last.get('path', '')}"
                + (f"  |  {last.get('summary', '')}" if last.get("summary") else ""))
        else:
            self._status.setText("等待 AI 修改代码…（AI 修改文件时，这里会实时显示每次修改的 diff）")

    # ── 事件轮询 ──
    def _poll(self):
        recs = drain_changes(50)
        if not recs:
            return
        existing = {(r.get("ts_full", ""), r.get("action", ""), r.get("path", "")) for r in self._records}
        added = 0
        for i, rec in enumerate(recs):
            key = (rec.get("ts_full", ""), rec.get("action", ""), rec.get("path", ""))
            if key in existing:
                continue  # 历史已加载，跳过重复
            existing.add(key)
            self._records.insert(0, rec)  # 最新在前，与列表行序一致
            label = _action_label(rec["action"])
            item = QListWidgetItem(
                f"[{rec['ts']}] {_action_icon(rec['action'])} {label}  {rec['path']}")
            item.setToolTip(rec["ts_full"])
            self._list.insertItem(0, item)  # 最新置顶
            added += 1
            if added == 1:
                self._list.setCurrentRow(0)  # 自动选中最新一条
        self._count_label.setText(f"{len(self._records)} 条")
        if added:
            last = self._records[0]
            self._status.setText(
                f"最新: {last['ts_full']}  {last['action']}  {last['path']}"
                + (f"  |  {last['summary']}" if last.get("summary") else ""))
        # AI 修改代码时自动打开面板
        if self._auto_open and not self.isVisible():
            self.show()
            self.raise_()

    def _show_record(self, row: int):
        if row < 0 or row >= len(self._records):
            return
        rec = self._records[row]
        head = (
            f"<b style='color:#00d4ff;'>{_action_label(rec['action']).upper()}</b> "
            f"<span style='color:#94a3b8;'>{rec['ts_full']}</span><br>"
            f"<span style='color:#fbbf24;'>{_html.escape(rec['path'])}</span>"
        )
        if rec.get("summary"):
            head += f"<br><span style='color:#10b981;'>{_html.escape(rec['summary'])}</span>"
        head += "<hr>"
        diff_text = rec.get("diff") or ""
        if not diff_text:
            # 旧版记录未保存内容时的友好提示
            if rec.get("action") == "create":
                hint = "（新建文件 — 该记录生成时未保存文件内容）"
            elif rec.get("action") == "delete":
                hint = "（删除文件 — 该记录未保存被删内容）"
            else:
                hint = "（无差异内容）"
            body = f"<div style='color:#94a3b8;'>{hint}</div>"
        else:
            body = _diff_to_html(diff_text)
        self._diff_view.setHtml(head + body)

    # ── 操作 ──
    def _clear(self):
        self._records.clear()
        self._list.clear()
        self._diff_view.clear()
        self._count_label.setText("0 条")
        self._status.setText("已清空，等待 AI 修改代码…")

    def show_panel(self):
        """手动打开面板（控制台按钮点击）"""
        self.show()
        self.raise_()
        self.activateWindow()

    # ── 窗口位置/大小持久化 ──
    def _save_geometry(self):
        """保存窗口位置和大小到 JSON 文件"""
        try:
            geom = self.saveGeometry().data().hex()
            _GEOMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            _GEOMETRY_FILE.write_text(
                json.dumps({"geometry": geom}, ensure_ascii=False),
                encoding="utf-8")
        except Exception as e:
            print(f"[面板] 保存窗口几何失败: {e}")

    def _restore_geometry(self):
        """从 JSON 文件恢复窗口位置和大小"""
        try:
            if not _GEOMETRY_FILE.exists():
                self.resize(880, 580)
                return
            data = json.loads(_GEOMETRY_FILE.read_text(encoding="utf-8"))
            geom = data.get("geometry")
            if geom and self.restoreGeometry(QByteArray.fromHex(bytes(geom, "ascii"))):
                # 验证窗口在可见屏幕内（防多显示器断开后窗口跑到屏幕外）
                from PyQt6.QtGui import QGuiApplication
                screen = QGuiApplication.screenAt(self.frameGeometry().center())
                if screen is None:
                    # 窗口在屏幕外，重置到主屏中心
                    primary = QGuiApplication.primaryScreen()
                    if primary:
                        geo = primary.availableGeometry()
                        self.move(geo.center().x() - 440, geo.center().y() - 290)
                        self.resize(880, 580)
            else:
                self.resize(880, 580)
        except Exception as e:
            print(f"[面板] 恢复窗口几何失败: {e}")
            self.resize(880, 580)

    def showEvent(self, event):
        """每次显示时恢复位置（防止被主窗口居中覆盖）"""
        super().showEvent(event)

    def hideEvent(self, event):
        """关闭/隐藏面板时保存位置"""
        self._save_geometry()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._save_geometry()
        self._timer.stop()
        super().closeEvent(event)
