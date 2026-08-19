"""
视频剪辑器 — 关键帧动画面板 (Phase 6)

支持属性：透明度/缩放/位置/旋转
支持缓动：线性/缓入/缓出/缓入缓出
快捷预设：淡入/淡出/Ken Burns
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.ui.video_editor.data_models import Clip, Keyframe
from src.ui.video_editor.keyframe import (
    KeyframeManager, create_fade_in_keyframes,
    create_fade_out_keyframes, create_zoom_in_keyframes, EASING_FUNCTIONS,
)
from ..theme import THEME


PROPERTY_NAMES = ["opacity", "scale_x", "scale_y", "pos_x", "pos_y", "rotation"]
PROPERTY_LABELS = {
    "opacity": "透明度", "scale_x": "缩放X", "scale_y": "缩放Y",
    "pos_x": "位置X", "pos_y": "位置Y", "rotation": "旋转",
}
EASING_LABELS = {
    "linear": "线性", "ease_in": "缓入", "ease_out": "缓出",
    "ease_in_out": "缓入缓出",
}


class KeyframePanel(QDialog):
    """关键帧动画面板"""

    keyframes_changed = pyqtSignal(object)  # Clip

    def __init__(self, clip: Clip, parent=None):
        super().__init__(parent)
        self._clip = clip
        if not getattr(clip, 'keyframes', None):
            clip.keyframes = []
        self.setWindowTitle(f"🎬 关键帧动画 — {clip.id[:8]}")
        self.resize(600, 480)
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 信息
        info = QLabel(
            f"片段 ID: {self._clip.id[:8]} | "
            f"时长: {self._clip.effective_duration:.1f}s | "
            f"类型: {self._clip.type}"
        )
        info.setStyleSheet(f"color:{THEME['text_secondary']}; font-size:11px;")
        layout.addWidget(info)

        # 快捷预设
        preset_group = QGroupBox("⚡ 快捷预设")
        pl = QHBoxLayout(preset_group)
        btn_fade_in = QPushButton("🌅 淡入")
        btn_fade_in.clicked.connect(self._preset_fade_in)
        btn_fade_out = QPushButton("🌇 淡出")
        btn_fade_out.clicked.connect(self._preset_fade_out)
        btn_zoom = QPushButton("🔍 Ken Burns")
        btn_zoom.clicked.connect(self._preset_zoom)
        btn_clear = QPushButton("🗑 全部清除")
        btn_clear.clicked.connect(self._preset_clear)
        for b in [btn_fade_in, btn_fade_out, btn_zoom, btn_clear]:
            pl.addWidget(b)
        pl.addStretch()
        layout.addWidget(preset_group)

        # 添加关键帧
        add_group = QGroupBox("➕ 添加关键帧")
        al = QHBoxLayout(add_group)

        al.addWidget(QLabel("属性:"))
        self._prop_combo = QComboBox()
        for p in PROPERTY_NAMES:
            self._prop_combo.addItem(PROPERTY_LABELS[p], p)
        al.addWidget(self._prop_combo)

        al.addWidget(QLabel("时间(s):"))
        self._time_spin = QDoubleSpinBox()
        self._time_spin.setRange(0, 9999)
        self._time_spin.setDecimals(2)
        self._time_spin.setValue(0.0)
        al.addWidget(self._time_spin)

        al.addWidget(QLabel("值:"))
        self._value_spin = QDoubleSpinBox()
        self._value_spin.setRange(-9999, 9999)
        self._value_spin.setDecimals(2)
        self._value_spin.setValue(1.0)
        al.addWidget(self._value_spin)

        al.addWidget(QLabel("缓动:"))
        self._easing_combo = QComboBox()
        for k, v in EASING_LABELS.items():
            self._easing_combo.addItem(v, k)
        al.addWidget(self._easing_combo)

        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self._add_keyframe)
        al.addWidget(btn_add)
        layout.addLayout(al)

        # 关键帧表格
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["属性", "时间(s)", "值", "缓动", ""])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, 1)

        # 关闭
        btn_close = QPushButton("✅ 完成")
        btn_close.clicked.connect(self._on_done)
        layout.addWidget(btn_close)

        self.setStyleSheet(f"""
            QDialog {{ background-color: {THEME['bg_main']}; }}
            QGroupBox {{ color: {THEME['text_primary']}; font-weight: bold; }}
            QLabel {{ color: {THEME['text_secondary']}; font-size:11px; }}
            QTableWidget {{ background-color: {THEME['bg_card']}; color: {THEME['text_primary']}; }}
            QTableWidget::item {{ padding: 4px; }}
        """)

    # ---- 表格刷新 ----

    def _refresh_table(self):
        kfs = KeyframeManager.get_keyframes(self._clip)
        self._table.setRowCount(len(kfs))
        for i, kf in enumerate(kfs):
            self._table.setItem(i, 0, QTableWidgetItem(PROPERTY_LABELS.get(kf.property, kf.property)))
            self._table.setItem(i, 1, QTableWidgetItem(f"{kf.time:.2f}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"{kf.value:.2f}"))
            self._table.setItem(i, 3, QTableWidgetItem(EASING_LABELS.get(kf.easing, kf.easing)))
            btn_del = QPushButton("✕")
            btn_del.setFixedWidth(25)
            btn_del.clicked.connect(lambda checked, kf_id=kf.id: self._delete_keyframe(kf_id))
            self._table.setCellWidget(i, 4, btn_del)

    # ---- 信号 ----

    def _add_keyframe(self):
        prop = self._prop_combo.currentData()
        time = self._time_spin.value()
        value = self._value_spin.value()
        easing = self._easing_combo.currentData()

        KeyframeManager.add_keyframe(self._clip, time, prop, value, easing)
        self._refresh_table()

    def _delete_keyframe(self, kf_id: str):
        KeyframeManager.remove_keyframe(self._clip, kf_id)
        self._refresh_table()

    def _preset_fade_in(self):
        self._clip.keyframes = [k for k in (self._clip.keyframes or [])
                                if k.property != "opacity"]
        create_fade_in_keyframes(self._clip, 1.0)
        self._refresh_table()

    def _preset_fade_out(self):
        self._clip.keyframes = [k for k in (self._clip.keyframes or [])
                                if k.property != "opacity"]
        create_fade_out_keyframes(self._clip)
        self._refresh_table()

    def _preset_zoom(self):
        self._clip.keyframes = [k for k in (self._clip.keyframes or [])
                                if k.property not in ("scale_x", "scale_y")]
        create_zoom_in_keyframes(self._clip)
        self._refresh_table()

    def _preset_clear(self):
        self._clip.keyframes = []
        self._refresh_table()

    def _on_done(self):
        self.keyframes_changed.emit(self._clip)
        self.accept()
