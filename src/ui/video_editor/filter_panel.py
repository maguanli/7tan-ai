"""
视频剪辑器 — 调色滤镜面板 (Phase 6)

提供：
- 预设滤镜一键应用
- 手动调整亮度/对比度/饱和度/色相/伽马
- 模糊/锐化/暗角滑块
- LUT 加载
- 实时预览（截图对比）
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QComboBox, QFileDialog, QGroupBox, QScrollArea,
    QWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.ui.video_editor.data_models import Clip, FilterConfig
from src.ui.video_editor.color_filter import ColorFilterEngine, PRESETS, FilterPreset
from ..theme import THEME


class FilterPanel(QDialog):
    """调色滤镜面板"""

    filter_applied = pyqtSignal(object)  # Clip

    def __init__(self, clip: Clip, parent=None):
        super().__init__(parent)
        self._clip = clip
        self._config = self._load_or_create_config()
        self._preset_index = 0
        self.setWindowTitle("🎨 调色滤镜")
        self.resize(520, 620)
        self._setup_ui()
        self._sync_ui_from_config()

    def _load_or_create_config(self) -> FilterConfig:
        """从 clip 加载已有滤镜配置，或创建新的"""
        if getattr(self._clip, 'filters', None) and self._clip.filters:
            for f in self._clip.filters:
                if isinstance(f, FilterConfig) and f.type == "color":
                    return f
        return FilterConfig(id="color_0", type="color", enabled=True)

    # ---- UI ----

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 预设
        preset_group = QGroupBox("📦 预设滤镜")
        pl = QVBoxLayout(preset_group)
        self._preset_combo = QComboBox()
        self._preset_combo.addItem("— 选择预设 —")
        for p in PRESETS:
            self._preset_combo.addItem(f"[{p.category}] {p.name}", p)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        pl.addWidget(self._preset_combo)
        layout.addWidget(preset_group)

        # 色彩调整
        color_group = QGroupBox("🌈 色彩调整")
        cl = QVBoxLayout(color_group)

        self._brightness = self._make_slider("亮度", -100, 100, 0, "%")
        self._contrast = self._make_slider("对比度", 0, 300, 100, "%")
        self._saturation = self._make_slider("饱和度", 0, 300, 100, "%")
        self._hue = self._make_slider("色相", -180, 180, 0, "°")
        self._gamma = self._make_slider("伽马", 50, 200, 100, "%")

        for s in [self._brightness, self._contrast, self._saturation, self._hue, self._gamma]:
            cl.addLayout(s)

        layout.addWidget(color_group)

        # 效果
        effect_group = QGroupBox("✨ 效果")
        el = QVBoxLayout(effect_group)

        self._blur = self._make_slider("模糊", 0, 100, 0)
        self._sharpen = self._make_slider("锐化", 0, 100, 0)
        self._vignette = self._make_slider("暗角", 0, 100, 0)

        for s in [self._blur, self._sharpen, self._vignette]:
            el.addLayout(s)

        layout.addWidget(effect_group)

        # LUT
        lut_layout = QHBoxLayout()
        self._lut_label = QLabel("LUT: 未加载")
        self._lut_label.setStyleSheet(f"color:{THEME['text_secondary']}; font-size:11px;")
        btn_load_lut = QPushButton("📂 加载 LUT")
        btn_load_lut.clicked.connect(self._on_load_lut)
        btn_clear_lut = QPushButton("✕")
        btn_clear_lut.setFixedWidth(30)
        btn_clear_lut.clicked.connect(self._on_clear_lut)
        lut_layout.addWidget(self._lut_label)
        lut_layout.addStretch()
        lut_layout.addWidget(btn_load_lut)
        lut_layout.addWidget(btn_clear_lut)
        layout.addLayout(lut_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("✅ 应用滤镜")
        btn_apply.clicked.connect(self._on_apply)
        btn_preview = QPushButton("👁 预览截图")
        btn_preview.clicked.connect(self._on_preview)
        btn_reset = QPushButton("↩ 重置")
        btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_preview)
        btn_layout.addWidget(btn_apply)
        layout.addLayout(btn_layout)

        self.setStyleSheet(f"""
            QDialog {{ background-color: {THEME['bg_main']}; }}
            QGroupBox {{ color: {THEME['text_primary']}; font-weight: bold; margin-top:8px; }}
            QLabel {{ color: {THEME['text_secondary']}; font-size:11px; }}
        """)

    def _make_slider(self, name: str, min_v: int, max_v: int,
                      default: int, suffix: str = "") -> QHBoxLayout:
        layout = QHBoxLayout()
        label = QLabel(f"{name}:")
        label.setFixedWidth(60)
        layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default)
        layout.addWidget(slider, 1)

        value_label = QLabel(f"{default}{suffix}")
        value_label.setFixedWidth(50)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(value_label)

        # 存储引用
        slider.valueChanged.connect(
            lambda v, vl=value_label, s=suffix: vl.setText(f"{v}{s}")
        )
        setattr(self, f"_slider_{name}", slider)
        setattr(self, f"_label_{name}", value_label)
        return layout

    # ---- 信号处理 ----

    def _on_preset_changed(self, idx: int):
        if idx <= 0:
            return
        preset: FilterPreset = self._preset_combo.currentData()
        if preset:
            self._apply_preset_to_ui(preset.config)

    def _apply_preset_to_ui(self, config: FilterConfig):
        self._brightness.setValue(int(config.brightness * 100))
        self._contrast.setValue(int(config.contrast * 100))
        self._saturation.setValue(int(config.saturation * 100))
        self._hue.setValue(int(config.hue))
        self._gamma.setValue(int(config.gamma * 100))
        self._blur.setValue(int(config.blur_strength * 100))
        self._sharpen.setValue(int(config.sharpen_strength * 100))
        self._vignette.setValue(int(config.vignette_strength * 100))

    def _sync_ui_from_config(self):
        c = self._config
        self._brightness.setValue(int(c.brightness * 100))
        self._contrast.setValue(int(c.contrast * 100))
        self._saturation.setValue(int(c.saturation * 100))
        self._hue.setValue(int(c.hue))
        self._gamma.setValue(int(c.gamma * 100))
        self._blur.setValue(int(c.blur_strength * 100))
        self._sharpen.setValue(int(c.sharpen_strength * 100))
        self._vignette.setValue(int(c.vignette_strength * 100))
        if c.lut_path:
            self._lut_label.setText(f"LUT: {Path(c.lut_path).name}")

    def _read_config_from_ui(self):
        c = self._config
        c.brightness = self._brightness.value() / 100.0
        c.contrast = self._contrast.value() / 100.0
        c.saturation = self._saturation.value() / 100.0
        c.hue = self._hue.value()
        c.gamma = self._gamma.value() / 100.0
        c.blur_strength = self._blur.value() / 100.0
        c.sharpen_strength = self._sharpen.value() / 100.0
        c.vignette_strength = self._vignette.value() / 100.0

    def _on_apply(self):
        self._read_config_from_ui()
        # 确保 clip 的 filters 列表存在
        if not getattr(self._clip, 'filters', None):
            self._clip.filters = []
        # 替换已有或追加
        replaced = False
        for i, f in enumerate(self._clip.filters):
            if isinstance(f, FilterConfig) and f.id == self._config.id:
                self._clip.filters[i] = self._config
                replaced = True
                break
        if not replaced:
            self._clip.filters.append(self._config)
        self.filter_applied.emit(self._clip)
        self.accept()

    def _on_preview(self):
        """预览截图"""
        self._read_config_from_ui()
        import tempfile
        import os
        from PyQt6.QtGui import QPixmap
        tmp = os.path.join(tempfile.gettempdir(), f"7tan_filter_preview_{self._clip.id[:6]}.png")
        ok = ColorFilterEngine.preview_filter(
            self._clip.source_path, self._config, tmp,
            seek_time=self._clip.source_start,
        )
        if ok:
            QMessageBox.information(self, "预览", f"预览图已生成:\n{tmp}")
        else:
            QMessageBox.warning(self, "预览失败", "滤镜预览失败，请检查 FFmpeg。")

    def _on_reset(self):
        self._config = FilterConfig(id="color_0", type="color", enabled=True)
        self._sync_ui_from_config()
        self._preset_combo.setCurrentIndex(0)

    def _on_load_lut(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "加载 LUT 文件", "",
            "LUT 文件 (*.cube *.3dl *.look);;所有文件 (*.*)"
        )
        if path:
            self._config.lut_path = path
            self._lut_label.setText(f"LUT: {Path(path).name}")

    def _on_clear_lut(self):
        self._config.lut_path = ""
        self._lut_label.setText("LUT: 未加载")

from pathlib import Path
