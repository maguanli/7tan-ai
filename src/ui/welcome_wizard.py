"""
新手引导向导 — 4步引导用户完成初始化配置

步骤:
  1. 欢迎页 — 告知需要自带 API Key，不花冤枉钱
  2. 推荐页 — 推荐 DeepSeek，模型对比 + 价格参考
  3. 填 Key 页 — 输入框 + 获取教程链接 + 跳过按钮
  4. 完成页 — "一切就绪！"进入主界面

触发条件：首次启动 或 从未填写过 API Key（config + DB 都为空）
"""
import webbrowser
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QWidget, QStackedWidget, QGraphicsDropShadowEffect,
    QSizePolicy, QCheckBox, QApplication,
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPixmap, QLinearGradient,
    QBrush, QIcon, QPen,
)
from PyQt6.QtCore import (
    Qt, QTimer, QSize,
)

from loguru import logger

# ============================================================
# 颜色方案 — 与 login_dialog 一致
# ============================================================

BG_DARK = "#0d1117"
BG_CARD = "#161b22"
BG_INPUT = "#21262d"
BORDER = "#30363d"
ACCENT = "#58a6ff"
ACCENT_HOVER = "#79c0ff"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
GOLD = "#d2991d"
GREEN = "#3fb950"
ORANGE = "#f0883e"
PURPLE = "#a371f7"

GRADIENT_START = "#1a1f35"
GRADIENT_END = "#0d1117"

# ============================================================
# 模型名称映射
# ============================================================

def _model_to_display(model: str) -> str:
    """数据库中的模型名 → 用户友好的显示名称"""
    if model == "deepseek-reasoner":
        return "deepseek-V4-Pro"
    if model == "deepseek-chat":
        return "deepseek-V4-Flash"
    if model == "deepseek-v4-flash":
        return "DeepSeek-V4-Flash-0731"
    return model


def _display_to_model(display: str) -> str:
    """用户友好的显示名称 → API 有效的模型名"""
    if not display or display == "deepseek-V4-Pro":
        return "deepseek-reasoner"
    if display == "deepseek-V4-Flash":
        return "deepseek-chat"
    if display == "DeepSeek-V4-Flash-0731":
        return "deepseek-v4-flash"
    return display


# ============================================================
# 步骤页面基类
# ============================================================


class WizardPage(QWidget):
    """向导页基类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 40, 44, 40)
        layout.setSpacing(20)

        # 标题
        self._title = QLabel()
        self._title.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(self._title)

        # 正文区域
        self._body = QVBoxLayout()
        self._body.setSpacing(14)
        layout.addLayout(self._body)

        layout.addStretch()
        self._content_layout = layout

    def set_title(self, text: str):
        self._title.setText(text)

    def add_text(self, text: str, size: int = 13, color: str = TEXT_SECONDARY, bold: bool = False):
        """添加一段说明文字"""
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        lbl.setFont(QFont("Microsoft YaHei", size, weight))
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
        self._body.addWidget(lbl)
        return lbl

    def add_spacer(self, height: int = 10):
        spacer = QFrame()
        spacer.setFixedHeight(height)
        spacer.setStyleSheet("background: transparent; border: none;")
        self._body.addWidget(spacer)


# ============================================================
# 第1步：欢迎页
# ============================================================

class WelcomePage(WizardPage):
    """欢迎使用 7Tan"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("👋 欢迎使用 7Tan")
        self.add_text("7Tan 是你的 AI 全能助手 — 开发软件、写代码、建网站、分析游戏、发布资源、聊天，全搞定。", size=14, color=TEXT_PRIMARY)
        self.add_spacer(8)
        self.add_text("⚠️ 重要提示：7Tan 不提供免费 AI 服务", size=14, color=ORANGE, bold=True)
        self.add_text(
            "你需要自备 API Key（推荐 DeepSeek，国内直连、便宜好用）。\n"
            "Key 只存储在你本地，我们不收集不上传。",
            size=13, color=TEXT_SECONDARY
        )
        self.add_spacer(14)
        self.add_text("💡 没有 Key 也能试用 3 次（免 Key）", size=13, color=GREEN)
        self.add_text("下一步将帮你了解如何获取 API Key →", size=13, color=TEXT_SECONDARY)


# ============================================================
# 第2步：推荐 DeepSeek
# ============================================================

class RecommendPage(WizardPage):
    """推荐 DeepSeek 模型"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("🔑 推荐使用 DeepSeek")

        self.add_text("为什么推荐 DeepSeek？", size=14, color=TEXT_PRIMARY, bold=True)
        self.add_text(
            "✅ 国内直连，无需梯子\n"
            "✅ 价格极低，性价比王者\n"
            "✅ 代码能力一流，中文友好\n"
            "✅ 官网充值，秒到账",
            size=13, color=TEXT_SECONDARY
        )

        self.add_spacer(14)

        # 模型对比表
        self.add_text("📊 模型对比", size=14, color=TEXT_PRIMARY, bold=True)

        table = QFrame()
        table.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        table_layout = QVBoxLayout(table)
        table_layout.setContentsMargins(16, 14, 16, 14)
        table_layout.setSpacing(8)

        # 表头
        header = QHBoxLayout()
        for col, w in [("模型", 160), ("输入价格", 100), ("输出价格", 100), ("特点", 160)]:
            lbl = QLabel(col)
            lbl.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
            lbl.setFixedWidth(w)
            header.addWidget(lbl)
        header.addStretch()
        table_layout.addLayout(header)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        table_layout.addWidget(sep)

        # 行数据
        rows = [
            ("V4-Pro ⭐", "¥3/百万", "¥6/百万", "最强推荐，写代码首选"),
            ("V4-Flash", "¥1/百万", "¥2/百万", "日常对话，性价比高"),
        ]
        for model, inp, out, desc in rows:
            row = QHBoxLayout()
            for col, w in [(model, 160), (inp, 100), (out, 100), (desc, 160)]:
                lbl = QLabel(col)
                color = ACCENT if "⭐" in col else TEXT_PRIMARY
                lbl.setFont(QFont("Microsoft YaHei", 12))
                lbl.setStyleSheet(f"color: {color}; background: transparent;")
                lbl.setFixedWidth(w)
                row.addWidget(lbl)
            row.addStretch()
            table_layout.addLayout(row)

        self._body.addWidget(table)

        # 充值参考
        self.add_spacer(10)
        self.add_text("💰 DeepSeek 充值参考：最低 ¥1 起充，日常使用每天 10-30 元绰绰有余", size=12, color=TEXT_SECONDARY)


# ============================================================
# 第3步：填写 API Key
# ============================================================

class FillKeyPage(WizardPage):
    """填写 DeepSeek API Key 和模型名称"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("🔐 填写你的 API Key")

        self.add_text("从 DeepSeek 官网获取 Key，粘贴到下方：", size=14, color=TEXT_PRIMARY)

        self.add_spacer(6)

        # 输入框
        self._input = QLineEdit()
        self._input.setPlaceholderText("sk-xxxxxxxxxxxxxxxxxxxxxxxx")
        self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.setFont(QFont("Consolas", 13))
        self._input.setMinimumHeight(44)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 10px 16px;
                font-family: "Consolas", "Courier New", monospace;
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
            }}
        """)
        self._body.addWidget(self._input)

        self.add_spacer(6)

        # 显示/隐藏切换
        self._btn_toggle = QPushButton("👁 显示 Key")
        self._btn_toggle.setFont(QFont("Microsoft YaHei", 11))
        self._btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                padding: 4px 0px;
                text-align: left;
            }}
            QPushButton:hover {{
                color: {ACCENT};
            }}
        """)
        self._btn_toggle.clicked.connect(self._toggle_visibility)
        self._body.addWidget(self._btn_toggle)

        self.add_spacer(14)

        # 模型名称输入框
        self.add_text("AI 模型名称（默认推荐）：", size=14, color=TEXT_PRIMARY)
        self.add_spacer(4)

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("deepseek-V4-Pro")
        self._model_input.setFont(QFont("Consolas", 13))
        self._model_input.setMinimumHeight(44)
        self._model_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 10px 16px;
                font-family: "Consolas", "Courier New", monospace;
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
            }}
        """)
        self._body.addWidget(self._model_input)

        self.add_spacer(4)
        self.add_text(
            "常用模型：deepseek-V4-Pro（推理能力最强）/ deepseek-chat（V4-Flash，快且便宜）",
            size=11, color=TEXT_SECONDARY
        )

        self.add_spacer(8)

        # 获取教程链接
        link_layout = QHBoxLayout()
        link_layout.setSpacing(12)

        btn_get_key = QPushButton("📖 如何获取 DeepSeek Key？")
        btn_get_key.setFont(QFont("Microsoft YaHei", 12))
        btn_get_key.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_get_key.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_HOVER};
            }}
        """)
        btn_get_key.clicked.connect(lambda: webbrowser.open("https://platform.deepseek.com/api_keys"))
        link_layout.addWidget(btn_get_key)

        link_layout.addStretch()
        self._body.addLayout(link_layout)

        self.add_spacer(10)
        self.add_text("🔒 Key 只保存在你的电脑上，通过 AES 加密存储，不会上传", size=12, color=TEXT_SECONDARY)

        # 尝试从数据库/配置文件加载已有配置，预填到输入框
        self._load_existing_config()

    # ------------------------------------------------------------------
    # 从数据库 / config.yaml 加载已有配置
    # ------------------------------------------------------------------

    def _load_existing_config(self):
        """从数据库优先、配置其次，加载已有的 Key 和模型名，预填到输入框"""
        key = ""
        model_db = ""

        # 1) 优先数据库（AI 系统实际读取的地方）
        try:
            from ..database.db import get_active_ai_config_raw
            cfg = get_active_ai_config_raw()
            if cfg and cfg.get("api_key", "").strip():
                key = cfg["api_key"].strip()
                model_db = cfg.get("model", "")
                logger.info(f"[Wizard] 从数据库加载已有配置, model={model_db}")
        except Exception as e:
            logger.debug(f"[Wizard] 数据库加载跳过: {e}")

        # 2) 数据库没 Key → 回退到 config.yaml
        if not key:
            try:
                from ..config.loader import load_config
                config = load_config()
                ds = config.get("ai", {}).get("configs", {}).get("deepseek", {})
                key = ds.get("api_key", "").strip()
                model_db = ds.get("model", "")
                if key:
                    logger.info(f"[Wizard] 从 config.yaml 加载已有配置, model={model_db}")
            except Exception as e:
                logger.debug(f"[Wizard] config.yaml 加载跳过: {e}")

        # 3) 预填
        if key:
            self._input.setText(key)
        if model_db:
            display_name = _model_to_display(model_db)
            self._model_input.setText(display_name)
            logger.info(f"[Wizard] 预填模型名: {model_db} → {display_name}")

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def _toggle_visibility(self):
        if self._input.echoMode() == QLineEdit.EchoMode.Password:
            self._input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._btn_toggle.setText("🙈 隐藏 Key")
        else:
            self._input.setEchoMode(QLineEdit.EchoMode.Password)
            self._btn_toggle.setText("👁 显示 Key")

    def get_key(self) -> str:
        return self._input.text().strip()

    def get_model(self) -> str:
        """返回 API 有效的模型名（自动映射）"""
        model = self._model_input.text().strip()
        return _display_to_model(model)


# ============================================================
# 第4步：完成
# ============================================================

class FinishPage(WizardPage):
    """完成引导"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("🎉 一切就绪！")

        self.add_text("7Tan 已经准备好为你工作了。", size=14, color=TEXT_PRIMARY)
        self.add_spacer(8)
        self.add_text("💡 小提示：", size=13, color=TEXT_PRIMARY, bold=True)
        self.add_text(
            "• 在左侧「AI 工作台」可以开始对话\n"
            "• 输入框支持拖入文件、图片识别\n"
            "• 设置页可以随时更换 API Key\n• 辅助软件安装的越齐全能力值越高",
            size=13, color=TEXT_SECONDARY
        )
        self.add_spacer(14)
        self.add_text("祝使用愉快！🚀", size=16, color=ACCENT, bold=True)


# ============================================================
# 主向导对话框
# ============================================================

class WelcomeWizard(QDialog):
    """新手引导向导 — 模态对话框"""

    wizard_finished = object()  # sentinel: 用户完成

    def __init__(self, parent=None, username: str | None = None):
        super().__init__(parent)
        self._username = username or ""
        self.setWindowTitle("7Tan — 新手指引")
        self.setFixedSize(560, 520)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 卡片容器
        card = QFrame()
        card.setObjectName("wizardCard")
        card.setStyleSheet(f"""
            QFrame#wizardCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {GRADIENT_START}, stop:1 {GRADIENT_END});
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 步骤指示器
        card_layout.addWidget(self._build_indicator())

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER}; margin: 0;")
        card_layout.addWidget(sep)

        # 页面堆栈
        self._stack = QStackedWidget()
        self._pages = [
            WelcomePage(),
            RecommendPage(),
            FillKeyPage(),
            FinishPage(),
        ]
        for p in self._pages:
            self._stack.addWidget(p)
        card_layout.addWidget(self._stack, 1)

        # 底部按钮
        card_layout.addWidget(self._build_bottom_bar())

        main_layout.addWidget(card)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        # 状态
        self._current_step = 0
        self._update_ui()

    def _build_indicator(self) -> QFrame:
        """构建步骤指示器"""
        indicator = QFrame()
        indicator.setStyleSheet(f"background-color: {BG_CARD}; border-radius: 0px;")
        indicator.setFixedHeight(60)

        layout = QHBoxLayout(indicator)
        layout.setContentsMargins(30, 0, 30, 0)
        layout.setSpacing(8)

        self._step_labels = []
        steps = ["1. 欢迎", "2. 推荐", "3. 填 Key", "4. 完成"]

        for i, text in enumerate(steps):
            # 点
            dot = QLabel("●" if i == 0 else "○")
            dot.setFont(QFont("Microsoft YaHei", 16))
            dot.setStyleSheet(f"color: {ACCENT}; background: transparent;")
            layout.addWidget(dot)

            # 文字
            lbl = QLabel(text)
            lbl.setFont(QFont("Microsoft YaHei", 12))
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY if i > 0 else TEXT_PRIMARY}; background: transparent;")
            layout.addWidget(lbl)

            # 连线
            if i < len(steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedWidth(20)
                line.setStyleSheet(f"color: {BORDER};")
                layout.addWidget(line)

            self._step_labels.append((dot, lbl))

        layout.addStretch()
        return indicator

    def _build_bottom_bar(self) -> QFrame:
        """构建底部按钮栏"""
        bar = QFrame()
        bar.setStyleSheet(f"background-color: {BG_CARD}; border-radius: 0px;")
        bar.setFixedHeight(64)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(30, 12, 30, 12)
        layout.setSpacing(12)

        # 上一步
        self._btn_prev = QPushButton("← 上一步")
        self._btn_prev.setFont(QFont("Microsoft YaHei", 12))
        self._btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_prev.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
                border-color: {TEXT_SECONDARY};
            }}
        """)
        self._btn_prev.clicked.connect(self._prev_step)
        layout.addWidget(self._btn_prev)

        layout.addStretch()

        # 打勾 — 不再提示复选框（勾选即持久化，真正生效）
        self._chk_disable = QCheckBox("不再提示（下次登录不再显示）")
        self._chk_disable.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chk_disable.toggled.connect(self._on_chk_toggled)
        self._chk_disable.setStyleSheet(f"""
            QCheckBox {{
                background: transparent;
                spacing: 0px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {BORDER};
                border-radius: 3px;
                background-color: {BG_INPUT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT};
                border-color: {ACCENT};
            }}
        """)
        layout.addWidget(self._chk_disable)

        # 不再提示
        self._btn_disable = QPushButton("不再提示")
        self._btn_disable.setFont(QFont("Microsoft YaHei", 11))
        self._btn_disable.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_disable.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                color: {ORANGE};
            }}
        """)
        self._btn_disable.clicked.connect(self._disable_wizard)
        layout.addWidget(self._btn_disable)

        # 跳过
        self._btn_skip = QPushButton("跳过")
        self._btn_skip.setFont(QFont("Microsoft YaHei", 12))
        self._btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_skip.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
            }}
        """)
        self._btn_skip.clicked.connect(self._skip)
        layout.addWidget(self._btn_skip)

        # 下一步 / 完成
        self._btn_next = QPushButton("下一步 →")
        self._btn_next.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_HOVER};
            }}
        """)
        self._btn_next.clicked.connect(self._next_step)
        layout.addWidget(self._btn_next)

        return bar

    def _update_ui(self):
        """更新 UI 状态"""
        # 步骤指示器
        for i, (dot, lbl) in enumerate(self._step_labels):
            if i < self._current_step:
                dot.setText("✓")
                dot.setStyleSheet(f"color: {GREEN}; background: transparent;")
                lbl.setStyleSheet(f"color: {GREEN}; background: transparent;")
            elif i == self._current_step:
                dot.setText("●")
                dot.setStyleSheet(f"color: {ACCENT}; background: transparent;")
                lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
            else:
                dot.setText("○")
                dot.setStyleSheet(f"color: {BORDER}; background: transparent;")
                lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")

        # 页面
        self._stack.setCurrentIndex(self._current_step)

        # 按钮
        is_first = self._current_step == 0
        is_last = self._current_step == len(self._pages) - 1

        self._btn_prev.setVisible(not is_first)
        self._btn_skip.setVisible(not is_last)
        # 打勾 + 不再提示 仅在第一页显示
        # 复选框与「不再提示」按钮在第1~3页可见（完成页无需再提示）
        self._chk_disable.setVisible(not is_last)
        self._btn_disable.setVisible(not is_last)

        if is_last:
            self._btn_next.setText("🎉 开始使用")
        else:
            self._btn_next.setText("下一步 →")

    def _prev_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._update_ui()

    def _next_step(self):
        if self._current_step < len(self._pages) - 1:
            self._current_step += 1
            self._update_ui()
        else:
            # 完成 → 保存 API Key；若勾选「不再提示」则持久化禁用（双保险）
            if self._chk_disable.isChecked():
                self._persist_disable()
            self._save_key()
            self.accept()

    def _skip(self):
        """跳过引导（若勾选「不再提示」则持久化禁用）"""
        if self._chk_disable.isChecked():
            self._persist_disable()
        self._save_key()
        self.accept()

    def _persist_disable(self):
        """持久化「不再提示」标记（仅当前用户）"""
        try:
            from ..utils.user_prefs import set_user_pref
            set_user_pref(self._username, "wizard_disabled", True)
            logger.info(f"[Wizard] 用户 {self._username or 'default'} 选择不再提示，已禁用")
        except Exception as e:
            logger.warning(f"[Wizard] 保存禁用设置失败: {e}")

    def _on_chk_toggled(self, checked: bool):
        """复选框勾选 → 立即持久化禁用（即点即生效，不依赖后续按钮）"""
        if checked:
            self._persist_disable()

    def _disable_wizard(self):
        """不再提示 — 仅对当前用户禁用新手引导"""
        self._persist_disable()
        self._save_key()
        self.accept()

    def _save_key(self):
        """保存用户输入的 API Key 和模型名称到 config.yaml 和数据库"""
        key = self._pages[2].get_key()
        model = self._pages[2].get_model()
        self._api_key = key  # 供外部获取

        if not key:
            return

        # 1. 保存到 config.yaml
        try:
            from ..config.loader import load_config, save_config
            config = load_config()
            # 更新 ai config
            if "ai" not in config:
                config["ai"] = {"active": "from_database", "configs": {}}
            if "configs" not in config["ai"]:
                config["ai"]["configs"] = {}
            if "deepseek" not in config["ai"]["configs"]:
                config["ai"]["configs"]["deepseek"] = {}

            config["ai"]["configs"]["deepseek"]["api_key"] = key
            config["ai"]["configs"]["deepseek"]["model"] = model
            config["ai"]["configs"]["deepseek"]["provider"] = "deepseek"
            config["ai"]["configs"]["deepseek"]["base_url"] = "https://api.deepseek.com/v1"
            save_config(config)
            logger.info(f"[Wizard] API Key + 模型({model}) 已保存到 config.yaml")
        except Exception as e:
            logger.warning(f"[Wizard] 保存到 config.yaml 失败: {e}")

        # 2. 保存到数据库 (AI 系统实际读取的地方)
        try:
            from ..database.db import save_ai_config, set_active_ai_config
            if model == "deepseek-v4-flash":
                save_ai_config(
                    config_key=model,
                    provider="deepseek",
                    model=model,
                    api_key=key,
                    base_url="https://api.deepseek.com/v1",
                    is_active=1,
                    context_window=1_000_000,
                    max_tokens=384_000,
                    temperature=1.0,
                    extra_config={"reasoning_effort": "max"},
                )
            else:
                save_ai_config(
                    config_key=model,
                    provider="deepseek",
                    model=model,
                    api_key=key,
                    base_url="https://api.deepseek.com/v1",
                    is_active=1,
                )
            set_active_ai_config(model)
            logger.info(f"[Wizard] API Key + 模型({model}) 已保存到数据库并激活")
        except Exception as e:
            logger.warning(f"[Wizard] 保存到数据库失败: {e}")

    def get_api_key(self) -> str:
        return getattr(self, '_api_key', '')

    def mousePressEvent(self, event):
        """窗口拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)


# ============================================================
# 公开接口
# ============================================================

def should_show_wizard(username: str | None = None) -> bool:
    """判断是否需要显示新手引导（按用户独立判断）
    
    只有该用户勾选「不再提示」才跳过，不影响其他用户。
    即使已有 Key，仍然显示引导（预填已有值，用户可修改）。
    """
    try:
        from ..utils.user_prefs import get_user_pref

        # 该用户选择了不再提示
        if get_user_pref(username or "", "wizard_disabled", False):
            return False

        # 始终显示引导（已有 Key 时会通过 _load_existing_config 预填）
        return True
    except Exception:
        return True


def show_welcome_wizard(parent=None, username: str | None = None) -> str | None:
    """
    显示新手引导向导。

    修复(2026-08-09): exec() 前先 show/raise_/activateWindow 并处理事件，
    确保向导窗口一定可见且在最前，避免用户看不到窗口导致"卡住无响应"。

    Returns:
        用户输入的 API Key（可能为空）
        None 表示用户关闭窗口取消
    """
    wizard = WelcomeWizard(parent, username=username)
    # 确保向导窗口显示在最前并被激活（防止窗口在后台/未聚焦，用户以为程序卡死）
    wizard.show()
    wizard.raise_()
    wizard.activateWindow()
    QApplication.processEvents()

    result = wizard.exec()

    if result == QDialog.DialogCode.Accepted:
        return wizard.get_api_key()
    return None
