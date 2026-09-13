"""
视频剪辑器 — 录屏设置对话框（Phase 4）

参见架构文档 8.5 录屏设置表：
    帧率 / 编码器 / 质量 / 系统音频 / 麦克风 / 麦克风音量 / 麦克风设备 / 保存目录
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QSlider, QLabel, QFileDialog, QLineEdit,
    QButtonGroup, QRadioButton, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from src.ui.video_editor.data_models import RecordingConfig
from src.ui.video_editor.screen_recorder import get_available_mics
from src.ui.video_editor.styles import TOOLBAR_STYLESHEET


class RecorderSettingsDialog(QDialog):
    """录屏设置对话框"""

    config_changed = pyqtSignal(object)  # RecordingConfig

    def __init__(self, current_config: RecordingConfig = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎥 录屏设置")
        self.setFixedSize(480, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #e0e0e0;
            }
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #aaccff;
            }
            QLabel {
                color: #ccc;
                font-size: 12px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background: #2a2a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #2a2a3a;
                color: #e0e0e0;
                selection-background-color: #3a3a5a;
            }
            QCheckBox {
                color: #ccc;
                font-size: 12px;
            }
            QSlider::groove:horizontal {
                background: #444;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #aaccff;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QRadioButton {
                color: #ccc;
                font-size: 12px;
            }
        """)

        self._config = current_config or RecordingConfig()
        self._mics = get_available_mics()

        self._setup_ui()
        self._load_config()
        QTimer.singleShot(0, self._refresh_audio_status)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ---- 录制模式 ----
        mode_group = QGroupBox("📺 录制模式")
        mode_layout = QVBoxLayout(mode_group)

        self._mode_btns = QButtonGroup(self)
        modes = [
            ("全屏", "fullscreen"),
            ("区域（拖拽选择）", "region"),
            ("窗口（点击选择）", "window"),
        ]
        mode_radio_layout = QHBoxLayout()
        for label, value in modes:
            rb = QRadioButton(label)
            rb.setStyleSheet("QRadioButton{color:#ccc;font-size:12px;padding:4px 8px;}")
            self._mode_btns.addButton(rb)
            rb.setProperty("mode_value", value)
            mode_radio_layout.addWidget(rb)
        mode_layout.addLayout(mode_radio_layout)

        layout.addWidget(mode_group)

        # ---- 视频参数 ----
        video_group = QGroupBox("🎬 视频参数")
        video_form = QFormLayout(video_group)
        video_form.setSpacing(8)

        self._fps_combo = QComboBox()
        self._fps_combo.addItems(["15", "24", "30", "60"])
        self._fps_combo.setCurrentText("30")
        video_form.addRow("帧率 (fps):", self._fps_combo)

        self._codec_combo = QComboBox()
        self._codec_combo.addItems([
            "H.264 (libx264) — 推荐",
            "H.265 (libx265) — 体积更小",
        ])
        video_form.addRow("编码器:", self._codec_combo)

        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(15, 35)
        self._quality_spin.setValue(23)
        self._quality_spin.setToolTip("CRF 值：越低画质越好，文件越大（推荐 18~28）")
        video_form.addRow("画质 (CRF):", self._quality_spin)

        self._quality_hint = QLabel("18=高质量  23=均衡  28=低质量")
        self._quality_hint.setStyleSheet("color:#888; font-size:10px; padding-left:4px;")
        video_form.addRow("", self._quality_hint)

        layout.addWidget(video_group)

        # ---- 音频参数 ----
        audio_group = QGroupBox("🎵 音频参数")
        audio_form = QFormLayout(audio_group)
        audio_form.setSpacing(8)

        # 系统音频设备检测状态提示
        self._sys_audio_status = QLabel("检测中…")
        self._sys_audio_status.setWordWrap(True)
        self._sys_audio_status.setStyleSheet(
            "color:#e8a33d; font-size:11px; padding:2px 4px;"
        )
        audio_form.addRow("系统声音:", self._sys_audio_status)

        self._sys_audio_check = QCheckBox("录制系统声音（WASAPI Loopback）")
        self._sys_audio_check.setChecked(True)
        audio_form.addRow(self._sys_audio_check)

        self._mic_check = QCheckBox("录制麦克风")
        self._mic_check.setChecked(False)
        self._mic_check.toggled.connect(self._on_mic_toggled)
        audio_form.addRow(self._mic_check)

        # 麦克风设备选择
        self._mic_device_combo = QComboBox()
        if self._mics:
            for mic in self._mics:
                self._mic_device_combo.addItem(mic["name"], mic["index"])
        else:
            self._mic_device_combo.addItem("默认麦克风", None)
        self._mic_device_combo.setEnabled(False)
        audio_form.addRow("麦克风设备:", self._mic_device_combo)

        # 麦克风音量
        mic_vol_layout = QHBoxLayout()
        self._mic_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._mic_vol_slider.setRange(0, 100)
        self._mic_vol_slider.setValue(80)
        self._mic_vol_slider.setEnabled(True)
        self._mic_vol_label = QLabel("80%")
        self._mic_vol_label.setStyleSheet("color:#ccc; font-size:12px; min-width:36px;")
        self._mic_vol_slider.valueChanged.connect(
            lambda v: self._mic_vol_label.setText(f"{v}%")
        )
        mic_vol_layout.addWidget(self._mic_vol_slider)
        mic_vol_layout.addWidget(self._mic_vol_label)
        audio_form.addRow("麦克风音量:", mic_vol_layout)

        layout.addWidget(audio_group)

        # ---- 保存 ----
        save_group = QGroupBox("💾 保存设置")
        save_layout = QHBoxLayout(save_group)
        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setPlaceholderText("默认为素材库目录")
        self._output_dir_edit.setReadOnly(True)
        save_layout.addWidget(self._output_dir_edit)

        browse_btn = QPushButton("📁 浏览")
        browse_btn.setStyleSheet(TOOLBAR_STYLESHEET)
        browse_btn.clicked.connect(self._browse_output_dir)
        save_layout.addWidget(browse_btn)

        layout.addWidget(save_group)

        layout.addStretch()

        # ---- 底部按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(TOOLBAR_STYLESHEET)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        start_btn = QPushButton("🎥 开始录制")
        start_btn.setStyleSheet(
            TOOLBAR_STYLESHEET +
            "background:#ff4444; color:#fff; font-weight:bold;"
        )
        start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(start_btn)

        layout.addLayout(btn_layout)

    def _load_config(self):
        """从现有配置加载到 UI"""
        c = self._config

        # 模式
        for btn in self._mode_btns.buttons():
            if btn.property("mode_value") == c.mode:
                btn.setChecked(True)
                break

        self._fps_combo.setCurrentText(str(c.fps))
        self._quality_spin.setValue(c.quality)

        codec_map = {"libx264": 0, "libx265": 1}
        self._codec_combo.setCurrentIndex(codec_map.get(c.codec, 0))

        self._sys_audio_check.setChecked(c.capture_system_audio)
        self._mic_check.setChecked(c.capture_mic)
        self._mic_vol_slider.setValue(int(c.mic_volume * 100))

        if c.mic_device_id is not None:
            for i in range(self._mic_device_combo.count()):
                if self._mic_device_combo.itemData(i) == c.mic_device_id:
                    self._mic_device_combo.setCurrentIndex(i)
                    break

        if c.output_dir:
            self._output_dir_edit.setText(c.output_dir)

    def _on_mic_toggled(self, checked: bool):
        self._mic_device_combo.setEnabled(checked)
        # 滑块始终可调，不依赖勾选状态

    def _refresh_audio_status(self):
        """检测系统音频捕获设备并显示状态（后台线程，避免卡 UI）"""
        import threading

        def _do():
            try:
                from src.ui.video_editor.screen_recorder import ScreenRecorder
                dev = ScreenRecorder()._detect_loopback_device()
                ok = bool(dev)
                msg = f"✅ 已检测到系统音频设备：{dev}" if ok else (
                    "⚠️ 未检测到系统音频捕获设备（立体声混音/Stereo Mix），"
                    "录屏将只有画面。请在系统声音设置中启用“立体声混音”。"
                )
                color = "#6fbf73" if ok else "#e8a33d"
            except Exception as e:
                msg = f"⚠️ 音频设备检测失败: {e}"
                color = "#e8a33d"

            def _apply():
                self._sys_audio_status.setText(msg)
                self._sys_audio_status.setStyleSheet(
                    f"color:{color}; font-size:11px; padding:2px 4px;"
                )
            QTimer.singleShot(0, _apply)

        threading.Thread(target=_do, daemon=True).start()

    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if path:
            self._output_dir_edit.setText(path)

    def _on_start(self):
        """点击开始 → 关闭对话框"""
        self.accept()

    def get_config(self) -> RecordingConfig:
        """对话框关闭后获取配置"""
        mode = "fullscreen"
        for btn in self._mode_btns.buttons():
            if btn.isChecked():
                mode = btn.property("mode_value")
                break

        codec = "libx264"
        if self._codec_combo.currentIndex() == 1:
            codec = "libx265"

        mic_device_id = None
        if self._mic_check.isChecked() and self._mic_device_combo.count() > 0:
            mic_device_id = self._mic_device_combo.currentData()

        config = RecordingConfig(
            mode=mode,
            fps=int(self._fps_combo.currentText()),
            codec=codec,
            quality=self._quality_spin.value(),
            capture_system_audio=self._sys_audio_check.isChecked(),
            capture_mic=self._mic_check.isChecked(),
            mic_volume=self._mic_vol_slider.value() / 100.0,
            mic_device_id=mic_device_id,
            output_dir=self._output_dir_edit.text() or "",
        )
        return config
