"""
AI 视频制作面板 UI — 图文成片

提供主题输入、脚本预览编辑、进度跟踪、一键生成功能。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QRadioButton, QComboBox, QListWidget,
    QListWidgetItem, QProgressBar, QGroupBox,
    QSizePolicy, QButtonGroup,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .data_models import SceneScript


_STYLE = """
QGroupBox { font-weight: bold; border: 1px solid #3a3a5c; border-radius: 8px;
    margin-top: 10px; padding-top: 16px; color: #e0e0e0; background: #1e1e32; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #7ec8e3; }
QPushButton { background: #2d6ff7; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-size: 13px; }
QPushButton:hover { background: #4a85f9; }
QPushButton:disabled { background: #444; color: #888; }
QRadioButton { color: #ccc; }
QComboBox { background: #2a2a3e; color: #e0e0e0; border: 1px solid #444; border-radius: 4px; padding: 4px 8px; }
QListWidget { background: #1a1a2e; color: #e0e0e0; border: 1px solid #333; border-radius: 6px; }
QListWidget::item { padding: 6px; border-bottom: 1px solid #2a2a3e; }
QListWidget::item:selected { background: #2d6ff7; }
QTextEdit { background: #1a1a2e; color: #e0e0e0; border: 1px solid #444; border-radius: 6px; padding: 6px; }
QTextEdit:focus { border-color: #2d6ff7; }
QLabel { color: #ccc; }
QProgressBar { border: none; border-radius: 4px; background: #2a2a3e; height: 8px; }
QProgressBar::chunk { background: #2ecc71; border-radius: 4px; }
"""


class SceneEditWidget(QWidget):
    """单个场景的编辑行"""
    changed = pyqtSignal(int, str, object)

    def __init__(self, scene: SceneScript, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        idx_label = QLabel(f"#{self.scene.index}")
        idx_label.setFixedWidth(28)
        idx_label.setStyleSheet("color: #7ec8e3; font-weight: bold;")
        layout.addWidget(idx_label)

        text_edit = QTextEdit()
        text_edit.setPlainText(self.scene.text)
        text_edit.setMaximumHeight(44)
        text_edit.setPlaceholderText("配音文案…")
        text_edit.textChanged.connect(
            lambda: self.changed.emit(self.scene.index, "text", text_edit.toPlainText()))
        layout.addWidget(text_edit, stretch=3)

        dur_label = QLabel(f"~{self.scene.duration:.0f}s")
        dur_label.setFixedWidth(36)
        dur_label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(dur_label)

        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(28, 28)
        btn_del.setStyleSheet("background: #c0392b; padding: 2px;")
        btn_del.clicked.connect(lambda: self.changed.emit(self.scene.index, "delete", None))
        layout.addWidget(btn_del)


class AIVideoPanel(QWidget):
    """AI 视频制作面板 — 图文成片"""

    script_generated = pyqtSignal(object)
    pipeline_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._script = None
        self._task = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(_STYLE)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── 主题输入 ──
        grp_input = QGroupBox("🎯 视频主题")
        input_layout = QVBoxLayout(grp_input)
        self.topic_edit = QTextEdit()
        self.topic_edit.setPlaceholderText(
            '描述你想制作的视频，如：\n"Python入门教程，3分钟，轻松风格，面向零基础"')
        self.topic_edit.setMaximumHeight(72)
        input_layout.addWidget(self.topic_edit)

        # 参数行
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("模式:"))
        self.mode_group = QButtonGroup(self)
        self.rb_text = QRadioButton("纯文本"); self.rb_text.setChecked(True)
        self.rb_image = QRadioButton("图文")
        self.rb_ai_image = QRadioButton("AI生图")
        for rb in [self.rb_text, self.rb_image, self.rb_ai_image]:
            self.mode_group.addButton(rb); params_layout.addWidget(rb)

        params_layout.addSpacing(12)
        params_layout.addWidget(QLabel("配音:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["女声-温柔", "女声-活泼", "男声-沉稳", "男声-磁性"])
        params_layout.addWidget(self.voice_combo)

        params_layout.addSpacing(12)
        params_layout.addWidget(QLabel("时长:"))
        self.dur_combo = QComboBox()
        self.dur_combo.addItems(["~1分钟", "~3分钟", "~5分钟", "~10分钟"])
        self.dur_combo.setCurrentIndex(1)
        params_layout.addWidget(self.dur_combo)

        params_layout.addSpacing(12)
        params_layout.addWidget(QLabel("风格:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["专业", "轻松", "科技", "搞笑"])
        params_layout.addWidget(self.style_combo)
        params_layout.addStretch()
        input_layout.addLayout(params_layout)

        # 生成脚本按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_gen_script = QPushButton("✨ 生成脚本")
        self.btn_gen_script.setStyleSheet("background: #f0a030;")
        self.btn_gen_script.clicked.connect(self._on_generate_script)
        btn_layout.addWidget(self.btn_gen_script)
        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)
        layout.addWidget(grp_input)

        # ── 分镜预览 ──
        grp_scenes = QGroupBox("📋 分镜预览")
        scenes_layout = QVBoxLayout(grp_scenes)
        self.scene_list = QListWidget()
        self.scene_list.setMinimumHeight(120)
        self.scene_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scenes_layout.addWidget(self.scene_list)
        btn_add = QPushButton("+ 添加场景")
        btn_add.clicked.connect(self._on_add_scene)
        scenes_layout.addWidget(btn_add)
        layout.addWidget(grp_scenes, stretch=2)

        # ── 底部 ──
        bottom_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #7ec8e3; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(self.status_label)
        run_layout = QHBoxLayout()
        run_layout.addStretch()
        self.btn_run = QPushButton("🚀 一键生成视频")
        self.btn_run.setStyleSheet(
            "background: #2ecc71; font-size: 14px; font-weight: bold; padding: 12px 30px;")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._on_run_pipeline)
        run_layout.addWidget(self.btn_run)
        run_layout.addStretch()
        bottom_layout.addLayout(run_layout)
        layout.addLayout(bottom_layout)

    # ── 公共方法 ──

    def set_script(self, script):
        """设置脚本并刷新预览"""
        self._script = script
        self._refresh_scene_list()
        self.btn_run.setEnabled(True)

    def set_task(self, task):
        """更新任务状态"""
        self._task = task
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(int(task.progress * 100))
        self.status_label.setText(f"{task.message}")
        if task.status == "done":
            self.status_label.setStyleSheet("color: #2ecc71; font-size: 13px; font-weight: bold;")
            self.progress_bar.setVisible(False)
        elif task.status == "failed":
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def _refresh_scene_list(self):
        self.scene_list.clear()
        if not self._script:
            return
        for scene in self._script.scenes:
            self._add_scene_item(scene)

    def _add_scene_item(self, scene):
        item = QListWidgetItem()
        widget = SceneEditWidget(scene)
        widget.changed.connect(self._on_scene_changed)
        item.setSizeHint(widget.sizeHint())
        self.scene_list.addItem(item)
        self.scene_list.setItemWidget(item, widget)

    # ── 槽 ──

    def _on_generate_script(self):
        topic = self.topic_edit.toPlainText().strip()
        if not topic:
            self.status_label.setText("请先输入视频主题")
            self.status_label.setStyleSheet("color: #f0a030;")
            return
        self.btn_gen_script.setEnabled(False)
        self.btn_gen_script.setText("⏳ 生成中…")
        self.status_label.setText("AI 正在生成脚本…")
        dur_map = {"~1分钟": 60, "~3分钟": 180, "~5分钟": 300, "~10分钟": 600}
        style_map = {"专业": "professional", "轻松": "casual", "科技": "tech", "搞笑": "funny"}
        self.script_generated.emit({
            "topic": topic,
            "style": style_map.get(self.style_combo.currentText(), "professional"),
            "duration": dur_map.get(self.dur_combo.currentText(), 180),
        })

    def _on_run_pipeline(self):
        dur_map = {"~1分钟": 60, "~3分钟": 180, "~5分钟": 300, "~10分钟": 600}
        style_map = {"专业": "professional", "轻松": "casual", "科技": "tech", "搞笑": "funny"}
        voice_map = {"女声-温柔": "female_gentle", "女声-活泼": "female_lively",
                     "男声-沉稳": "male_calm", "男声-磁性": "male_deep"}
        mode = "text_only"
        if self.rb_image.isChecked():
            mode = "image"
        elif self.rb_ai_image.isChecked():
            mode = "ai_image"
        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳ 制作中…")
        self.pipeline_requested.emit({
            "topic": self.topic_edit.toPlainText().strip(),
            "mode": mode,
            "style": style_map.get(self.style_combo.currentText(), "professional"),
            "duration": dur_map.get(self.dur_combo.currentText(), 180),
            "voice": voice_map.get(self.voice_combo.currentText(), "female_gentle"),
        })

    def _on_scene_changed(self, index, field, value):
        if field == "delete" and self._script:
            self._script.scenes = [s for s in self._script.scenes if s.index != index]
            self._refresh_scene_list()

    def _on_add_scene(self):
        if not self._script:
            return
        new_idx = len(self._script.scenes) + 1
        scene = SceneScript(index=new_idx, text=f"场景 {new_idx} 的文案…", duration=30.0)
        self._script.scenes.append(scene)
        self._add_scene_item(scene)

    def on_generation_done(self):
        self.btn_gen_script.setEnabled(True)
        self.btn_gen_script.setText("✨ 生成脚本")

    def on_pipeline_done(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("🚀 一键生成视频")
