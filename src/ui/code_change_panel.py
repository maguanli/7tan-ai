"""
实时变更面板 — 监控 AI 偷偷改文件（方案 A 双栏大师视图 + 方案 D 今日热力图摘要）

功能（v6 升级）：
  - 顶部「今日监控概览」：今日修改次数 / 涉及文件数 / 24 小时热力图
      ▁▂▄▆█ 一眼看出 AI 今天哪个时段在疯狂改代码
  - 左侧：修改记录列表（时间 + 操作 + 文件 + 变更统计 +n/-m + 状态徽章 ✅/⚠️/❌），最新置顶
      支持【实时搜索】路径/摘要 + 【操作类型过滤】下拉
  - 右侧：diff 高亮视图（+绿 / -红 / @@蓝 / ---+++紫）+ 变更统计头 + 上一处/下一处差异跳转
  - 📌 自动打开开关：AI 修改代码时自动弹出面板并置顶（默认开启）
  - 🗑 清空历史记录
  - QTimer 轮询 code_change_bus（线程安全队列 + jsonl 跨进程增量，实时兜底）
  - 性能护栏：隐藏停表 / 512KB 限读 / 500 条上限 / 渲染防抖（防未响应）
"""
from __future__ import annotations

import html as _html
import json
from datetime import datetime
import time
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QListWidget, QListWidgetItem, QSplitter, QApplication,
    QLineEdit, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, QByteArray
from PyQt6.QtGui import QTextCursor

# 绝对路径锚定项目 data 目录（与 code_change_bus 一致，不依赖启动 CWD）
_GEOMETRY_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "panel_geometry.json"

from ..utils.code_change_bus import drain_changes, load_history, history_tail_size

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

# 状态徽章（status 字段：ok / failed / rolled_back，旧记录无 status → 默认 ✅）
_STATUS_BADGES = {
    "ok": ("✅", "#10b981"),
    "success": ("✅", "#10b981"),
    "failed": ("❌", "#ef4444"),
    "error": ("❌", "#ef4444"),
    "rolled_back": ("⚠️", "#f59e0b"),
    "rollback": ("⚠️", "#f59e0b"),
}

# 热力图等级（今日每小时的修改次数 → 字符）
_HEAT_LEVELS = (("█", 8), ("▆", 5), ("▄", 3), ("▂", 1), ("▁", 0))

# v5 性能护栏（防 UI 主线程卡死/未响应）：
#  1. 面板隐藏时停止全部轮询定时器（空闲零负载）
#  2. 单次文件轮询最多读 512KB（大 diff 分多次消化，每轮 UI 工作量有上限）
#  3. 内存最多保留 500 条记录（长期运行不无界增长）
_MAX_RECORDS = 500
_MAX_TAIL_BYTES = 512 * 1024


def _action_icon(action: str) -> str:
    return _ACTION_ICONS.get(action, "📄")


def _action_label(action: str) -> str:
    return _ACTION_LABELS.get(action, action)


def _status_badge(status) -> tuple:
    """状态徽章 → (emoji, 颜色)；旧记录/空值默认 ok"""
    if not status:
        return _STATUS_BADGES["ok"]
    return _STATUS_BADGES.get(str(status).lower(), _STATUS_BADGES["ok"])


def _diff_stats(diff_text: str) -> tuple:
    """统计 diff 新增/删除行数（忽略 ---/+++/@@ 头，供列表 +n/-m 显示）"""
    adds = dels = 0
    if not diff_text:
        return 0, 0
    for ln in diff_text.splitlines():
        if ln.startswith(("+++", "---", "@@")):
            continue
        if ln.startswith("+"):
            adds += 1
        elif ln.startswith("-"):
            dels += 1
    return adds, dels


def _heat_bar(count: int) -> str:
    """修改次数 → 热力图字符（0→▁ 低 →█ 高）"""
    for ch, threshold in _HEAT_LEVELS:
        if count >= threshold:
            return ch
    return "▁"


def _short_path(path: str) -> str:
    """隐藏项目根目录前缀，只显示相对路径（D:/7tan/7tanAI/src/ui/x.py → src/ui/x.py）

    记录里可能是绝对路径（Windows 反斜杠）或相对路径；统一规范化后
    若以项目根开头则去掉前缀。非项目内路径原样返回。
    """
    if not path:
        return ""
    try:
        root = str(Path(__file__).resolve().parent.parent.parent).replace("/", "\\")
        p = str(path).replace("/", "\\")
        if p.lower().startswith(root.lower()):
            return p[len(root):].lstrip("\\/")
    except Exception:
        pass
    return str(path)


def _diff_to_html(diff_text: str) -> str:
    """diff 文本 → 行级高亮 HTML（超过 500 行截断，防 UI 卡死）"""
    if not diff_text:
        return '<div style="color:#94a3b8;">（无差异内容）</div>'
    _MAX_LINES = 500
    lines = diff_text.splitlines()
    truncated = len(lines) > _MAX_LINES
    if truncated:
        omitted = len(lines) - _MAX_LINES
        lines = lines[:_MAX_LINES]
    parts = []
    for line in lines:
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
    if truncated:
        parts.append(
            f'<div style="color:#f59e0b;font-weight:bold;padding:6px 0;">⚠️ diff 过长，已省略后 {omitted} 行（完整内容请查看文件本身）</div>'
        )
    return "".join(parts)


class CodeChangePanel(QWidget):
    """代码修改实时面板（独立窗口：监控 AI 偷偷改了哪些文件）"""

    def __init__(self, parent=None, auto_open: bool = False):
        super().__init__(parent)
        self.setWindowTitle("🔧 代码修改实时 — 监控 AI 改文件")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self._auto_open = auto_open
        self._restore_geometry()
        self._records: list[dict] = []      # 全量记录（最新在前）
        self._visible: list[int] = []       # 过滤后的记录索引（对应列表行）
        self._seen_keys: set = set()        # seq 去重
        self._hist_cursor = 0               # jsonl 增量读取游标（跨进程实时兜底）
        self._build_ui()
        self._load_history_records()
        # 快速定时器：只拉内存队列（120ms，无文件 I/O，不卡 UI）
        # 注意：定时器不在此启动 —— 面板启动时创建但未显示，
        # 若此时运行轮询等于无意义的后台空转（历史已全量加载）。
        # 首次 showEvent 才启动，hideEvent 停止 → 隐藏期零负载。
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        # 慢速定时器：jsonl 文件增量读取（600ms，跨进程兜底；单次限 512KB，UI 线程每轮有上限）
        self._file_timer = QTimer(self)
        self._file_timer.timeout.connect(self._poll_file_tail)
        # 守护定时器（隐藏期也运行，1.5s 一次极轻量）：只 stat jsonl 大小，
        # 有新增才小量读取 → 触发自动打开。修复【面板隐藏时不轮询 → 自动打开
        # 失效、与控制台文件操作不同步】问题。
        # ⚠️ 启动时初始化为当前历史大小：历史记录是过去发生的修改，
        #    不应触发自动弹出（否则每次启动 7Tan 都会弹出小窗口）。
        #    只有本次运行中新增的修改事件（jsonl 变大）才会自动打开面板。
        self._guard_last_size = history_tail_size()
        self._last_user_hide = time.time()  # 初始=当前时间：启动阶段不触发自动弹出（防止启动即弹窗）
        self._guard_timer = QTimer(self)
        self._guard_timer.timeout.connect(self._guard_poll)
        self._guard_timer.start(1500)
        # 渲染防抖：高频新事件时 300ms 内只渲染最后一次
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(300)
        self._render_timer.timeout.connect(self._render_current_row)
        # 搜索过滤防抖：输入 200ms 后才重建列表
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._apply_filter)

        # 几何防抖保存：拖动/缩放 300ms 后落盘，任何退出方式都不丢
        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.setInterval(300)
        self._geometry_timer.timeout.connect(self._save_geometry)
        # 应用退出兜底：主窗口关闭时子窗口不触发 closeEvent/hideEvent，
        # 必须靠 aboutToQuit 保证关闭软件前保存窗口位置与大小
        _app = QApplication.instance()
        if _app is not None:
            try:
                _app.aboutToQuit.connect(self._save_geometry)
            except Exception as _qe:
                print(f"[面板] 注册退出保存失败: {_qe}")

    # ── UI ──
    def _build_ui(self):
        T = CHANGE_THEME
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # ── 顶部工具栏：标题 | 计数 | 搜索 | 类型过滤 | 自动打开 | 清空 | 关闭 ──
        bar = QHBoxLayout()
        title = QLabel("🔧 代码修改实时")
        title.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{T['text_primary']};")
        bar.addWidget(title)

        self._count_label = QLabel("0/0 条")
        self._count_label.setStyleSheet(
            f"color:{T['text_secondary']};font-size:11px;padding:0 6px;")
        bar.addWidget(self._count_label)

        # 搜索框（方案 A：实时搜索路径/摘要）
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍 搜索文件/摘要…")
        self._search_box.setFixedWidth(170)
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setStyleSheet(f"""
            QLineEdit {{
                background: {T['bg']}; color: {T['text_primary']};
                border: 1px solid {T['border']}; border-radius: 4px;
                padding: 3px 8px; font-size: 11px;
            }}
            QLineEdit:focus {{ border: 1px solid {T['accent2']}88; }}
        """)
        self._search_box.textChanged.connect(
            lambda *_: self._filter_timer.start())
        bar.addWidget(self._search_box)

        # 操作类型过滤下拉（方案 A）
        self._type_box = QComboBox()
        self._type_box.addItem("全部类型", None)
        for k in ("write", "replace", "create", "delete", "config"):
            self._type_box.addItem(f"{_ACTION_ICONS[k]} {_ACTION_LABELS[k]}", k)
        self._type_box.setFixedWidth(112)
        self._type_box.setStyleSheet(f"""
            QComboBox {{
                background: {T['bg']}; color: {T['text_primary']};
                border: 1px solid {T['border']}; border-radius: 4px;
                padding: 3px 6px; font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
            QComboBox QAbstractItemView {{
                background: {T['bg']}; color: {T['text_primary']};
                selection-background-color: {T['accent']}66;
                font-size: 11px;
            }}
        """)
        # 先添加完所有项再连接（避免构建期误触发）
        self._type_box.currentIndexChanged.connect(self._apply_filter)
        bar.addWidget(self._type_box)
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

        # ── 今日监控概览（方案 D：次数 / 文件数 / 24小时热力图）──
        self._overview_label = QLabel("📊 今日 0 次 · 0 个文件 · 频率(时) " + "▁" * 24)
        self._overview_label.setStyleSheet(
            f"color:{T['text_secondary']};font-size:11px;padding:3px 8px;"
            f"background:{T['bg']};border:1px solid {T['border']};border-radius:4px;")
        self._overview_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._overview_label)

        # ── 中部：左记录列表 + 右 diff 视图（方案 A 双栏大师视图）──
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

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)
        # diff 工具栏：统计信息 + 上一处/下一处差异跳转
        diff_bar = QHBoxLayout()
        self._diff_stats_label = QLabel("选择一条记录查看 diff")
        self._diff_stats_label.setStyleSheet(
            f"color:{T['text_secondary']};font-size:11px;padding:0 4px;")
        diff_bar.addWidget(self._diff_stats_label)
        diff_bar.addStretch()
        prev_btn = QPushButton("⬆ 上一处")
        prev_btn.setFixedHeight(24)
        prev_btn.setToolTip("跳到上一个差异块 (@@)")
        prev_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['accent']}22; color: {T['text_primary']};
                border: 1px solid {T['border']}; border-radius: 4px;
                padding: 1px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {T['accent']}55; }}
        """)
        prev_btn.clicked.connect(lambda: self._goto_diff(-1))
        diff_bar.addWidget(prev_btn)
        next_btn = QPushButton("⬇ 下一处")
        next_btn.setFixedHeight(24)
        next_btn.setToolTip("跳到下一个差异块 (@@)")
        next_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['accent']}22; color: {T['text_primary']};
                border: 1px solid {T['border']}; border-radius: 4px;
                padding: 1px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {T['accent']}55; }}
        """)
        next_btn.clicked.connect(lambda: self._goto_diff(1))
        diff_bar.addWidget(next_btn)
        right_layout.addLayout(diff_bar)

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
        right_layout.addWidget(self._diff_view, 1)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 580])
        layout.addWidget(splitter, 1)

        # ── 底部状态 ──
        self._status = QLabel("等待 AI 修改代码…")
        self._status.setStyleSheet(
            f"color:{T['text_secondary']};font-size:11px;padding:2px 4px;")
        layout.addWidget(self._status)

    # ── 历史加载（重启后不丢失）──
    def _load_history_records(self):
        """打开面板时加载记录：内存队列 + 历史文件双通道合并（seq 去重，最新在前）"""
        from ..utils.code_change_bus import history_tail_size
        # ① 内存队列中的事件（若 jsonl 写入失败仍有兜底）
        queued = []
        try:
            queued = drain_changes(1000)
        except Exception:
            pass
        # ② 历史文件全量
        recs = load_history(300)
        # ③ 按 seq 合并去重（旧记录无 seq 用 ts+action+path 兜底）
        merged: dict = {}
        for rec in queued + recs:
            key = rec.get("seq") or (
                rec.get("ts_full", ""), rec.get("action", ""), rec.get("path", ""))
            merged[key] = rec
        # ④ 排序：v4 后 seq 为字符串（pid-时间戳-序号），旧记录为 int，
        #    直接对 seq 排序会 int/str 崩溃 → 统一用 ts_full 字符串排序
        items = sorted(
            merged.values(),
            key=lambda r: (r.get("ts_full") or "", str(r.get("seq") or "")),
            reverse=True)
        for rec in items:
            self._records.append(rec)
            key = rec.get("seq") or (
                rec.get("ts_full", ""), rec.get("action", ""), rec.get("path", ""))
            self._seen_keys.add(key)
        self._apply_filter()
        self._update_summary()
        if self._records:
            last = self._records[0]
            self._status.setText(
                f"最新: {last.get('ts_full', '')}  {last.get('action', '')}  {_short_path(last.get('path', ''))}"
                + (f"  |  {last.get('summary', '')}" if last.get("summary") else ""))
        else:
            self._status.setText("等待 AI 修改代码…（AI 修改文件时，这里会实时显示每次修改的 diff）")
        # 历史已全量加载 → 游标移到文件末尾，之后只增量读新事件
        self._hist_cursor = history_tail_size()

    # ── 事件轮询 ──
    def _poll(self):
        """快速轮询：只拉内存队列（无文件 I/O）"""
        recs = drain_changes(50)
        self._ingest_records(recs)

    def _poll_file_tail(self):
        """慢速轮询：jsonl 文件增量读取（跨进程兜底，单次限 512KB 防卡）"""
        try:
            from ..utils.code_change_bus import read_history_tail
            tail, cursor = read_history_tail(self._hist_cursor, _MAX_TAIL_BYTES)
            if tail is None:
                # 文件被修剪（超限删头部）→ 重置游标重读
                self._hist_cursor = 0
                tail, cursor = read_history_tail(self._hist_cursor, _MAX_TAIL_BYTES)
            self._hist_cursor = cursor
            self._ingest_records(tail or [])
        except Exception:
            pass

    def _guard_poll(self):
        """隐藏期守护轮询：仅 stat 文件大小（微秒级），有新增才小量读 jsonl 尾部。

        面板隐藏时主轮询停止，若不做守护则永远感知不到 AI 文件修改
        （自动打开失效 + 与控制台操作不同步）。守护只在有变化时做一次
        小量读取（≤64KB），负载可忽略。
        """
        if self.isVisible():
            return
        try:
            from ..utils.code_change_bus import history_tail_size
            size = history_tail_size()
            if size == self._guard_last_size:
                return
            self._guard_last_size = size
            self._poll_file_tail()
        except Exception:
            pass

    def _ingest_records(self, recs: list):
        """统一入库：seq 去重 + 插入全量（最新置顶）→ 重建过滤列表 + 刷新今日概览"""
        if not recs:
            return
        added = 0
        for rec in recs:
            key = rec.get("seq") or (
                rec.get("ts_full", ""), rec.get("action", ""), rec.get("path", ""))
            if key in self._seen_keys:
                continue
            self._seen_keys.add(key)
            self._records.insert(0, rec)  # 最新在前
            added += 1
        # 内存上限：超 500 条丢最旧（防长期运行无界增长）
        while len(self._records) > _MAX_RECORDS:
            self._records.pop()
        self._apply_filter()
        self._update_summary()
        if added:
            last = self._records[0]
            self._status.setText(
                f"最新: {last['ts_full']}  {last['action']}  {_short_path(last['path'])}"
                + (f"  |  {last['summary']}" if last.get("summary") else ""))
            # 渲染防抖：300ms 内连续到达的事件只渲染最后一次
            self._render_timer.start()
        # AI 修改代码时自动打开面板（用户手动关闭后 20 秒内不自动弹出，防打扰）
        if self._auto_open and not self.isVisible():
            if time.time() - self._last_user_hide > 20:
                self.show()
                self.raise_()

    # ── 过滤 / 概览（方案 A + D 核心）──
    def _apply_filter(self):
        """按搜索词 + 操作类型过滤 → 重建列表（搜索防抖 200ms 后调用）"""
        if not hasattr(self, "_list"):
            return
        kw = self._search_box.text().strip().lower()
        typ = self._type_box.currentData()
        self._visible = []
        for i, r in enumerate(self._records):
            if typ and r.get("action") != typ:
                continue
            if kw:
                hay = " ".join((
                    str(r.get("path", "")),
                    str(r.get("summary", "")),
                    str(r.get("diff", ""))[:200],
                )).lower()
                if kw not in hay:
                    continue
            self._visible.append(i)
        # 重建列表（≤500 条，200ms 防抖后重建开销可忽略）
        self._list.blockSignals(True)
        self._list.clear()
        for idx in self._visible:
            r = self._records[idx]
            adds, dels = _diff_stats(r.get("diff", ""))
            badge, _ = _status_badge(r.get("status"))
            stats = f"  (+{adds} -{dels})" if (adds or dels) else ""
            item = QListWidgetItem(
                f"[{r.get('ts', '')}] {_action_icon(r.get('action', ''))} "
                f"{_action_label(r.get('action', ''))}  {_short_path(r.get('path', ''))}"
                f"{stats} {badge}")
            item.setToolTip(
                f"{r.get('ts_full', '')}\n"
                f"{_action_label(r.get('action', ''))} {r.get('path', '')}"
                + (f"\n摘要: {r.get('summary', '')}" if r.get("summary") else ""))
            self._list.addItem(item)
        self._list.blockSignals(False)
        if self._visible:
            self._list.setCurrentRow(0)
            self._show_record(self._visible[0])
        else:
            self._diff_view.setHtml(
                "<div style='color:#94a3b8;'>（无匹配记录）</div>")
        self._count_label.setText(f"{len(self._visible)}/{len(self._records)} 条")

    def _update_summary(self):
        """刷新顶部今日监控概览：今日次数 / 涉及文件数 / 24小时热力图"""
        today = datetime.now().strftime("%Y-%m-%d")
        per_hour = [0] * 24
        files: set = set()
        total = 0
        for r in self._records:
            ts = r.get("ts_full", "")
            if ts.startswith(today):
                try:
                    per_hour[int(ts[11:13])] += 1
                except Exception:
                    continue
                total += 1
                files.add(r.get("path", ""))
        bars = "".join(_heat_bar(v) for v in per_hour)
        self._overview_label.setText(
            f"📊 今日 {total} 次 · {len(files)} 个文件 · 频率(时) {bars}")
        tip_lines = [f"{i:02d}时: {v}次" for i, v in enumerate(per_hour) if v]
        self._overview_label.setToolTip(
            "24 小时修改热力图（0点→23点，▁低 █高）\n"
            + ("\n".join(tip_lines) if tip_lines else "今日暂无修改"))

    def _goto_diff(self, direction: int):
        """跳转到下一个/上一个差异块（@@ 行），direction: 1=下一处, -1=上一处"""
        doc = self._diff_view.document()
        cursor = self._diff_view.textCursor()
        cur_block = cursor.blockNumber()
        targets = [b for b in range(doc.blockCount())
                   if doc.findBlockByNumber(b).text().startswith("@@")]
        if not targets:
            return
        if direction > 0:
            nxt = next((t for t in targets if t > cur_block), targets[0])
        else:
            nxt = next((t for t in reversed(targets) if t < cur_block), targets[-1])
        c = QTextCursor(doc.findBlockByNumber(nxt))
        self._diff_view.setTextCursor(c)
        self._diff_view.ensureCursorVisible()

    def _render_current_row(self):
        """防抖后的实际渲染（300ms 合并窗口结束才执行）"""
        row = self._list.currentRow()
        if row >= 0:
            self._show_record(row)

    def _show_record(self, row: int):
        """row = 列表行号（过滤后可见列表）→ 映射到全量 _records 渲染 diff"""
        if row < 0 or row >= len(self._visible):
            return
        rec = self._records[self._visible[row]]
        badge, bcolor = _status_badge(rec.get("status"))
        adds, dels = _diff_stats(rec.get("diff", ""))
        head = (
            f"<span style='color:{bcolor};font-size:14px;'>{badge}</span> "
            f"<b style='color:#00d4ff;'>{_action_label(rec['action']).upper()}</b> "
            f"<span style='color:#94a3b8;'>{rec['ts_full']}</span>"
            f"<span style='color:#10b981;'>  +{adds} -{dels}</span><br>"
            f"<span style='color:#fbbf24;'>{_html.escape(_short_path(rec['path']))}</span>"
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
        # 顶部 diff 工具栏统计
        self._diff_stats_label.setText(
            f"{badge} {_action_label(rec['action'])}  +{adds} -{dels}"
            + (f"  ·  {rec.get('summary', '')}" if rec.get("summary") else ""))

    # ── 操作 ──
    def _clear(self):
        self._records.clear()
        self._visible.clear()
        self._seen_keys.clear()
        self._list.clear()
        self._diff_view.clear()
        self._count_label.setText("0/0 条")
        self._update_summary()
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

    def moveEvent(self, event):
        """移动窗口 → 防抖保存位置"""
        super().moveEvent(event)
        self._geometry_timer.start()

    def resizeEvent(self, event):
        """缩放窗口 → 防抖保存大小"""
        super().resizeEvent(event)
        self._geometry_timer.start()

    def showEvent(self, event):
        """显示面板 → 停止守护、恢复主轮询，并立即补读一次（防隐藏期间错过事件）"""
        super().showEvent(event)
        self._guard_timer.stop()
        self._timer.start(120)
        self._file_timer.start(600)
        try:
            self._poll_file_tail()
        except Exception:
            pass

    def hideEvent(self, event):
        """隐藏面板 → 保存位置 + 停止主轮询，改跑轻量守护（隐藏期仍能感知修改并自动弹出）"""
        self._save_geometry()
        self._last_user_hide = time.time()
        self._timer.stop()
        self._file_timer.stop()
        self._guard_timer.start(1500)
        super().hideEvent(event)

    def closeEvent(self, event):
        self._save_geometry()
        self._timer.stop()
        self._file_timer.stop()
        self._render_timer.stop()
        super().closeEvent(event)
