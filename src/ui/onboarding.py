"""
新人引导遮罩层 — 主界面交互式引导

在主窗口上叠加半透明遮罩，高亮关键 UI 区域，逐步引导新用户了解功能。
首次启动且完成欢迎向导后自动显示，可在任意步骤跳过或关闭。

设计：
  - 半透明遮罩覆盖整个主窗口
  - 目标区域"挖空"（透过遮罩显示）
  - 旁边显示提示气泡，含「下一步」「跳过」按钮
  - 完成后写入配置，不再显示
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QGraphicsOpacityEffect,
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath, QRegion,
    QLinearGradient,
)
from PyQt6.QtCore import (
    Qt, QRect, QPoint, QTimer, pyqtSignal, QEasingCurve,
    QPropertyAnimation,
)

from loguru import logger

# ============================================================
# 颜色方案 — 与 app.py 的 THEME 保持一致
# ============================================================
OVERLAY_COLOR = QColor(0, 0, 0, 160)       # 遮罩颜色
HIGHLIGHT_BORDER = QColor("#00d4ff")        # 高亮边框（青色）
HIGHLIGHT_BORDER_WIDTH = 3
BUBBLE_BG = QColor("#1a1f35")              # 气泡背景
BUBBLE_BORDER = QColor("#30363d")
BUBBLE_TEXT = QColor("#e6edf3")
BUBBLE_ACCENT = QColor("#00d4ff")
BUBBLE_TITLE = QColor("#ffffff")


# ============================================================
# 引导步骤定义
# ============================================================
class OnboardingStep:
    """单个引导步骤"""

    def __init__(
        self,
        target_widget_name: str,
        title: str,
        description: str,
        placement: str = "right",  # right / bottom / left / top
        offset_x: int = 0,
        offset_y: int = 0,
    ):
        self.target_widget_name = target_widget_name
        self.title = title
        self.description = description
        self.placement = placement
        self.offset_x = offset_x
        self.offset_y = offset_y


# 默认引导步骤 — 按主窗口中的控件 objectName
DEFAULT_STEPS = [
    OnboardingStep(
        "sidebar_frame",
        "📋 侧边栏导航",
        "在这里切换功能模块：\n"
        "• 💬 AI 工作台 — 对话、写代码、分析\n"
        "• 📦 资源管理 — 管理已发布的游戏/软件\n"
        "• ⚙️ 任务监控 — 查看自动采集进度\n"
        "• 🔧 设置 — 配置 API Key、模型等",
        placement="right",
        offset_x=8,
        offset_y=-40,
    ),
    OnboardingStep(
        "workspace_chat",
        "💬 AI 工作台 — 核心功能区",
        "这就是你的 AI 助手主战场！\n"
        "• 输入问题或任务，AI 会自动执行\n"
        "• 支持拖入文件、图片识别\n"
        "• 左侧对话列表可切换历史会话\n"
        "• 内置浏览器可打开网页进行操作",
        placement="bottom",
        offset_x=0,
        offset_y=16,
    ),
    OnboardingStep(
        "proStatusFrame",
        "⚡ 能力值与专业版",
        "这里显示你的「能力值」评分和账户状态。\n"
        "• 免费版：基础功能，能力值上限 80\n"
        "• 专业版：解锁全部功能，+20 能力值\n"
        "• 专业版支持更多模型、更高并发",
        placement="right",
        offset_x=8,
        offset_y=0,
    ),
    OnboardingStep(
        "status_bar_info",
        "📌 状态栏",
        "底部状态栏显示当前连接状态、\n"
        "登录用户名和系统通知信息。\n"
        "出问题时先看这里！",
        placement="top",
        offset_x=0,
        offset_y=-16,
    ),
]


# ============================================================
# 遮罩覆盖层
# ============================================================
class OnboardingOverlay(QWidget):
    """半透明遮罩 + 高亮目标区域 + 提示气泡"""

    # 信号
    finished = pyqtSignal()        # 全部完成
    skipped = pyqtSignal()         # 用户跳过

    def __init__(self, parent, steps: list[OnboardingStep] | None = None):
        super().__init__(parent)
        self._parent = parent
        self._steps = steps or DEFAULT_STEPS
        self._current_idx = 0
        self._target_rects: dict[str, QRect] = {}  # 目标控件在全局坐标中的位置

        # 覆盖整个父窗口
        self.setGeometry(parent.rect())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.raise_()

        # 气泡容器（浮动在遮罩上方）
        self._bubble = _BubbleWidget(self)
        self._bubble.next_clicked.connect(self._on_next)
        self._bubble.skip_clicked.connect(self._on_skip)
        self._bubble.hide()

        # 入口动画
        self._fade_in()

        # 延迟显示第一步（等窗口完全渲染）
        QTimer.singleShot(400, self._show_current_step)

    # ------------------------------------------------------------------
    def _fade_in(self):
        """淡入动画"""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.start()

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        """绘制半透明遮罩 + 高亮窗口"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 全屏半透明遮罩
        painter.fillRect(self.rect(), OVERLAY_COLOR)

        # 挖空当前步骤的目标区域
        if 0 <= self._current_idx < len(self._steps):
            step = self._steps[self._current_idx]
            target_rect = self._get_target_rect(step)
            if target_rect and target_rect.isValid():
                # 扩展一点边距，让高亮区域比控件稍大
                expanded = target_rect.adjusted(-6, -6, 6, 6)
                # 挖空
                path = QPainterPath()
                path.addRect(self.rect())
                path.addRoundedRect(
                    float(expanded.x()), float(expanded.y()),
                    float(expanded.width()), float(expanded.height()),
                    8.0, 8.0,
                )
                painter.setClipPath(path)
                painter.fillRect(self.rect(), OVERLAY_COLOR)

                # 恢复裁剪，画高亮边框（发光效果）
                painter.setClipping(False)
                pen = QPen(HIGHLIGHT_BORDER, HIGHLIGHT_BORDER_WIDTH)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(
                    float(expanded.x()), float(expanded.y()),
                    float(expanded.width()), float(expanded.height()),
                    8.0, 8.0,
                )

                # 外发光（再画一层更宽、更透明的边框）
                glow_pen = QPen(QColor(0, 212, 255, 80), HIGHLIGHT_BORDER_WIDTH + 4)
                painter.setPen(glow_pen)
                painter.drawRoundedRect(
                    float(expanded.x() - 2), float(expanded.y() - 2),
                    float(expanded.width() + 4), float(expanded.height() + 4),
                    10.0, 10.0,
                )

        painter.end()

    # ------------------------------------------------------------------
    def _get_target_rect(self, step: OnboardingStep) -> QRect | None:
        """查找目标控件并返回在 overlay 坐标系中的矩形"""
        target_widget = self._find_widget_by_name(self._parent, step.target_widget_name)
        if target_widget is None:
            logger.warning(f"[Onboarding] 未找到目标控件: {step.target_widget_name}")
            return None

        # 获取控件在父窗口中的全局位置
        pos = target_widget.mapTo(self._parent, QPoint(0, 0))
        size = target_widget.size()
        rect = QRect(pos, size)

        # 应用偏移
        rect.translate(step.offset_x, step.offset_y)
        return rect

    def _find_widget_by_name(self, root, name: str) -> QWidget | None:
        """递归查找指定 objectName 的控件"""
        if root.objectName() == name:
            return root
        for child in root.findChildren(QWidget):
            if child.objectName() == name:
                return child
        return None

    # ------------------------------------------------------------------
    def _show_current_step(self):
        """显示当前步骤"""
        if self._current_idx >= len(self._steps):
            self._finish()
            return

        step = self._steps[self._current_idx]
        target_rect = self._get_target_rect(step)

        # 如果找不到目标控件，跳过当前步骤
        if target_rect is None:
            logger.warning(f"[Onboarding] 跳过步骤 {self._current_idx}: 找不到 {step.target_widget_name}")
            self._current_idx += 1
            QTimer.singleShot(100, self._show_current_step)
            return

        # 计算气泡位置
        bubble_pos = self._calc_bubble_position(target_rect, step.placement)
        self._bubble.move(bubble_pos)

        # 更新内容
        self._bubble.set_content(
            step.title,
            step.description,
            is_last=(self._current_idx == len(self._steps) - 1),
            step_num=self._current_idx + 1,
            total=len(self._steps),
        )

        # 显示 + 动画
        self._bubble.show()
        self._bubble.raise_()

        # 重绘遮罩
        self.update()

    def _calc_bubble_position(self, target_rect: QRect, placement: str) -> QPoint:
        """根据目标矩形和放置位置计算气泡左上角坐标"""
        bubble_w = self._bubble.width()
        bubble_h = self._bubble.height()
        margin = 16

        if placement == "right":
            x = target_rect.right() + margin
            y = target_rect.center().y() - bubble_h // 2
        elif placement == "left":
            x = target_rect.left() - bubble_w - margin
            y = target_rect.center().y() - bubble_h // 2
        elif placement == "bottom":
            x = target_rect.center().x() - bubble_w // 2
            y = target_rect.bottom() + margin
        elif placement == "top":
            x = target_rect.center().x() - bubble_w // 2
            y = target_rect.top() - bubble_h - margin
        else:
            x = target_rect.right() + margin
            y = target_rect.center().y() - bubble_h // 2

        # 确保不超出窗口
        x = max(8, min(x, self.width() - bubble_w - 8))
        y = max(8, min(y, self.height() - bubble_h - 8))

        return QPoint(int(x), int(y))

    # ------------------------------------------------------------------
    def _on_next(self):
        """下一步"""
        self._current_idx += 1
        self._bubble.hide()
        QTimer.singleShot(200, self._show_current_step)

    def _on_skip(self):
        """跳过"""
        logger.info("[Onboarding] 用户跳过引导")
        self.skipped.emit()
        self._close()

    def _finish(self):
        """完成所有步骤"""
        logger.info("[Onboarding] 引导完成")
        self.finished.emit()
        self._close()

    def _close(self):
        """淡出并关闭"""
        self._bubble.hide()
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        """点击遮罩空白区域 → 跳到下一步（比"跳过"更友好）"""
        # 不处理，让用户必须点气泡按钮（避免误触跳过）
        pass


# ============================================================
# 提示气泡
# ============================================================
class _BubbleWidget(QFrame):
    """引导提示气泡 — 浮动在遮罩层上方"""

    next_clicked = pyqtSignal()
    skip_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 200)
        self.setObjectName("onboardingBubble")
        self.setStyleSheet(f"""
            #onboardingBubble {{
                background-color: {BUBBLE_BG.name()};
                border: 1px solid {BUBBLE_BORDER.name()};
                border-radius: 12px;
            }}
        """)

        # 阴影效果（简单实现：用内边距模拟）
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(8)

        # 步骤指示器
        self._step_label = QLabel()
        self._step_label.setFont(QFont("Microsoft YaHei", 10))
        self._step_label.setStyleSheet(f"color: {BUBBLE_ACCENT.name()}; background: transparent;")
        layout.addWidget(self._step_label)

        # 标题
        self._title_label = QLabel()
        self._title_label.setFont(QFont("Microsoft YaHei", 15, QFont.Weight.Bold))
        self._title_label.setStyleSheet(f"color: {BUBBLE_TITLE.name()}; background: transparent;")
        self._title_label.setWordWrap(True)
        layout.addWidget(self._title_label)

        # 描述
        self._desc_label = QLabel()
        self._desc_label.setFont(QFont("Microsoft YaHei", 12))
        self._desc_label.setStyleSheet(f"color: {BUBBLE_TEXT.name()}; background: transparent;")
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label, 1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._skip_btn = QPushButton("跳过引导")
        self._skip_btn.setFont(QFont("Microsoft YaHei", 11))
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #8b949e;
                border: none;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                color: #e6edf3;
            }}
        """)
        self._skip_btn.clicked.connect(self.skip_clicked.emit)
        btn_layout.addWidget(self._skip_btn)

        btn_layout.addStretch()

        self._next_btn = QPushButton("下一步 →")
        self._next_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUBBLE_ACCENT.name()};
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{
                background-color: #33ddff;
            }}
        """)
        self._next_btn.clicked.connect(self.next_clicked.emit)
        btn_layout.addWidget(self._next_btn)

        layout.addLayout(btn_layout)

    def set_content(self, title: str, description: str, is_last: bool, step_num: int, total: int):
        """更新气泡内容"""
        self._step_label.setText(f"✨ 新手指引  {step_num} / {total}")
        self._title_label.setText(title)
        self._desc_label.setText(description)

        if is_last:
            self._next_btn.setText("🎉 开始使用")
        else:
            self._next_btn.setText("下一步 →")


# ============================================================
# 公开接口
# ============================================================

_ONBOARDING_DONE_KEY = "onboarding_completed"


def is_onboarding_done() -> bool:
    """判断新人引导是否已完成"""
    try:
        from ..config.loader import load_config
        config = load_config()
        return config.get("app", {}).get(_ONBOARDING_DONE_KEY, False)
    except Exception:
        return False


def mark_onboarding_done():
    """标记新人引导已完成"""
    try:
        from ..config.loader import load_config, save_config
        config = load_config()
        if "app" not in config:
            config["app"] = {}
        config["app"][_ONBOARDING_DONE_KEY] = True
        save_config(config)
        logger.info("[Onboarding] 已标记引导完成")
    except Exception as e:
        logger.warning(f"[Onboarding] 标记失败: {e}")


def show_onboarding(parent, steps: list[OnboardingStep] | None = None) -> OnboardingOverlay | None:
    """
    在父窗口上显示新人引导遮罩。

    返回 OnboardingOverlay 实例，连接其 finished / skipped 信号以处理后续逻辑。
    如果引导已完成或没有步骤，返回 None。
    """
    if is_onboarding_done():
        logger.info("[Onboarding] 引导已完成，跳过")
        return None

    if steps is not None and len(steps) == 0:
        return None

    overlay = OnboardingOverlay(parent, steps)

    def _on_done():
        mark_onboarding_done()

    overlay.finished.connect(_on_done)
    overlay.skipped.connect(mark_onboarding_done)

    logger.info("[Onboarding] 显示新人引导遮罩")
    return overlay
