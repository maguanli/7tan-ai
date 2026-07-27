"""
登录对话框
PyQt6 原生控件，精美渐变色设计。

功能:
  - 用户名/手机号 + 密码登录
  - 记住30天
  - 忘记密码 → 跳转 7tan.com
  - 跳过试用（3次）
  - 错误提示
  - 登录中加载状态
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QApplication,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QLinearGradient,
    QBrush, QPainter,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect,
    QPoint, pyqtSignal, QSize,
)

from loguru import logger

from ..security.auth_client import login, LoginFailed, NetworkError, ServerError
from ..security.token_store import save_token, is_token_available
from ..security.trial_store import use_trial, has_trials, MAX_TRIALS

# ============================================================
# 颜色方案
# ============================================================

BG_DARK = "#0d1117"
BG_CARD = "#161b22"
BG_INPUT = "#21262d"
BORDER = "#30363d"
ACCENT = "#58a6ff"
ACCENT_HOVER = "#79c0ff"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_ERROR = "#f85149"
GREEN = "#3fb950"
GOLD = "#d2991d"

# 渐变
GRADIENT_START = "#1a1f35"
GRADIENT_END = "#0d1117"


# ============================================================
# 登录对话框
# ============================================================

class LoginDialog(QDialog):
    """登录对话框 — 模态窗口"""

    # 信号：登录成功
    login_success = pyqtSignal(dict)  # 传递用户信息

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("7Tan — 登录")
        self.setFixedSize(420, 520)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self._user_info: dict | None = None
        self._dragging = False
        self._drag_pos: QPoint | None = None

        self._setup_ui()
        self._apply_styles()

    # ============================================================
    # UI 构建
    # ============================================================

    def _setup_ui(self):
        """构建 UI 布局"""
        # 外层容器（带圆角和阴影）
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 卡片容器
        self._card = QFrame(self)
        self._card.setObjectName("card")
        self._card.setFixedSize(420, 520)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 100))
        self._card.setGraphicsEffect(shadow)

        # 主布局
        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(0)

        # --- 标题栏（可拖拽） ---
        title_bar = QHBoxLayout()

        # LOGO 图标
        logo_label = QLabel("🎮")
        logo_label.setFont(QFont("Segoe UI Emoji", 28))
        title_bar.addWidget(logo_label)

        title_bar.addStretch()

        # 关闭按钮
        btn_close = QPushButton("✕")
        btn_close.setObjectName("btnClose")
        btn_close.setFixedSize(32, 32)
        btn_close.clicked.connect(self.reject)
        title_bar.addWidget(btn_close)

        layout.addLayout(title_bar)
        layout.addSpacing(8)

        # --- 标题 ---
        title = QLabel("欢迎使用 7Tan")
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("登录您的 7Tan 账号")
        subtitle.setFont(QFont("Microsoft YaHei", 12))
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        # --- 用户名 ---
        lbl_user = QLabel("用户名 / 手机号")
        lbl_user.setFont(QFont("Microsoft YaHei", 11))
        lbl_user.setStyleSheet(f"color: {TEXT_SECONDARY}; margin-bottom: 4px;")
        layout.addWidget(lbl_user)

        self._input_user = QLineEdit()
        self._input_user.setPlaceholderText("请输入用户名或手机号")
        self._input_user.setFont(QFont("Microsoft YaHei", 13))
        self._input_user.setMinimumHeight(42)
        layout.addWidget(self._input_user)
        layout.addSpacing(16)

        # --- 密码 ---
        lbl_pwd = QLabel("密码")
        lbl_pwd.setFont(QFont("Microsoft YaHei", 11))
        lbl_pwd.setStyleSheet(f"color: {TEXT_SECONDARY}; margin-bottom: 4px;")
        layout.addWidget(lbl_pwd)

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(0)

        self._input_pwd = QLineEdit()
        self._input_pwd.setPlaceholderText("请输入密码")
        self._input_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._input_pwd.setFont(QFont("Microsoft YaHei", 13))
        self._input_pwd.setMinimumHeight(42)
        pwd_row.addWidget(self._input_pwd)

        # 显示/隐藏密码按钮
        self._btn_toggle_pwd = QPushButton("👁")
        self._btn_toggle_pwd.setObjectName("btnTogglePwd")
        self._btn_toggle_pwd.setFixedSize(42, 42)
        self._btn_toggle_pwd.setToolTip("显示/隐藏密码")
        self._btn_toggle_pwd.clicked.connect(self._toggle_password)
        pwd_row.addWidget(self._btn_toggle_pwd)

        layout.addLayout(pwd_row)
        layout.addSpacing(12)

        # --- 记住密码 + 忘记密码 ---
        bottom_row = QHBoxLayout()

        self._chk_remember = QCheckBox("记住 30 天")
        self._chk_remember.setFont(QFont("Microsoft YaHei", 11))
        self._chk_remember.setChecked(True)
        bottom_row.addWidget(self._chk_remember)

        bottom_row.addStretch()

        btn_forgot = QPushButton("忘记密码？")
        btn_forgot.setObjectName("btnLink")
        btn_forgot.setFont(QFont("Microsoft YaHei", 11))
        btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_forgot.clicked.connect(self._on_forgot_password)
        bottom_row.addWidget(btn_forgot)

        layout.addLayout(bottom_row)
        layout.addSpacing(20)

        # --- 错误提示 ---
        self._lbl_error = QLabel("")
        self._lbl_error.setFont(QFont("Microsoft YaHei", 11))
        self._lbl_error.setStyleSheet(f"color: {TEXT_ERROR};")
        self._lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_error.setWordWrap(True)
        self._lbl_error.setVisible(False)
        layout.addWidget(self._lbl_error)
        layout.addSpacing(8)

        # --- 登录按钮 ---
        self._btn_login = QPushButton("登  录")
        self._btn_login.setObjectName("btnLogin")
        self._btn_login.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self._btn_login.setMinimumHeight(44)
        self._btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_login.clicked.connect(self._on_login)
        layout.addWidget(self._btn_login)
        layout.addSpacing(16)

        # --- 试用入口 ---
        trial_row = QHBoxLayout()
        trial_row.addStretch()

        trials_left = MAX_TRIALS  # 默认显示
        try:
            trials_left = __import__("src.security.trial_store", fromlist=["get_trials_left"]).get_trials_left()
        except Exception:
            pass

        btn_skip = QPushButton(f"跳过，试用 {trials_left} 次（免费）")
        btn_skip.setObjectName("btnLink")
        btn_skip.setFont(QFont("Microsoft YaHei", 11))
        btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skip.clicked.connect(self._on_skip_trial)
        trial_row.addWidget(btn_skip)

        trial_row.addStretch()
        layout.addLayout(trial_row)

        layout.addStretch()

        # --- 底部 ---
        footer = QPushButton("没有账号？访问 7tan.com 注册")
        footer.setObjectName("btnLink")
        footer.setFont(QFont("Microsoft YaHei", 10))
        footer.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.clicked.connect(lambda: self._open_url("https://www.7tan.com/register/"))
        footer.setStyleSheet(f"""
            QPushButton#btnLink {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-weight: normal;
                padding: 4px;
            }}
            QPushButton#btnLink:hover {{
                color: {ACCENT};
            }}
        """)
        layout.addWidget(footer)

    # ============================================================
    # 样式
    # ============================================================

    def _apply_styles(self):
        """应用 QSS 样式"""
        self.setStyleSheet(f"""
            QDialog {{
                background: transparent;
            }}
            #card {{
                background: qlineargradient(
                    x1:0 y1:0, x2:0 y2:1,
                    stop:0 {GRADIENT_START}, stop:1 {GRADIENT_END}
                );
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            QLineEdit {{
                background-color: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                selection-background-color: {ACCENT};
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT};
            }}
            #btnLogin {{
                background-color: {ACCENT};
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }}
            #btnLogin:hover {{
                background-color: {ACCENT_HOVER};
            }}
            #btnLogin:pressed {{
                background-color: #4090d0;
            }}
            #btnLogin:disabled {{
                background-color: {BG_INPUT};
                color: {TEXT_SECONDARY};
            }}
            #btnClose {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
            }}
            #btnClose:hover {{
                background-color: rgba(255,255,255,0.08);
                color: {TEXT_PRIMARY};
            }}
            #btnLink {{
                background: transparent;
                color: {ACCENT};
                border: none;
                text-decoration: underline;
            }}
            #btnLink:hover {{
                color: {ACCENT_HOVER};
            }}
            #btnTogglePwd {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 16px;
                border-radius: 0 8px 8px 0;
            }}
            #btnTogglePwd:hover {{
                background-color: rgba(255,255,255,0.05);
            }}
            QCheckBox {{
                color: {TEXT_SECONDARY};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {BORDER};
                border-radius: 4px;
                background-color: {BG_INPUT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT};
                border-color: {ACCENT};
            }}
        """)

    # ============================================================
    # 窗口拖拽
    # ============================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_pos:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ============================================================
    # 事件处理
    # ============================================================

    def _toggle_password(self):
        """切换密码显示/隐藏"""
        if self._input_pwd.echoMode() == QLineEdit.EchoMode.Password:
            self._input_pwd.setEchoMode(QLineEdit.EchoMode.Normal)
            self._btn_toggle_pwd.setText("🙈")
        else:
            self._input_pwd.setEchoMode(QLineEdit.EchoMode.Password)
            self._btn_toggle_pwd.setText("👁")

    def _open_url(self, url: str):
        """在浏览器中打开 URL"""
        import webbrowser
        webbrowser.open(url)

    def _on_forgot_password(self):
        """忘记密码 → 打开 7tan.com"""
        self._open_url("https://www.7tan.com/forgot-password/")
        self._show_error("")  # 清除错误

    def _on_login(self):
        """登录按钮"""
        username = self._input_user.text().strip()
        password = self._input_pwd.text()

        if not username:
            self._show_error("请输入用户名或手机号")
            self._input_user.setFocus()
            return

        if not password:
            self._show_error("请输入密码")
            self._input_pwd.setFocus()
            return

        # 进入加载状态
        self._set_loading(True)
        self._show_error("")

        # 异步登录
        QTimer.singleShot(100, lambda: self._do_login(username, password))

    def _do_login(self, username: str, password: str):
        """执行登录请求"""
        try:
            remember = self._chk_remember.isChecked()
            result = login(username, password, remember_me=remember)

            # 保存 Token
            save_token(
                token=result["token"],
                username=result["username"],
                level=result["level"],
                pro_expires=result.get("pro_expires", 0),
                expires_in=result.get("expires_in", 2592000),
            )

            self._user_info = result
            logger.info(f"[Login] 登录成功: {result['username']} (等级: {result['level']})")

            # 短暂延迟后关闭对话框
            QTimer.singleShot(400, self._accept)

        except LoginFailed as e:
            self._set_loading(False)
            self._show_error(str(e))
        except NetworkError as e:
            self._set_loading(False)
            self._show_error(str(e))
        except ServerError as e:
            self._set_loading(False)
            self._show_error(str(e))
        except Exception as e:
            self._set_loading(False)
            self._show_error(f"未知错误: {e}")
            logger.exception(e)

    def _on_skip_trial(self):
        """跳过试用"""
        if not has_trials():
            self._show_error("试用次数已用完，请登录后使用")
            return

        remaining = use_trial()
        if remaining <= 0:
            self._show_error("这是最后一次试用，下次请登录")

        logger.info(f"[Login] 跳过登录，试用模式（剩余 {remaining} 次）")
        self._user_info = {
            "token": "",
            "username": f"试用用户",
            "level": "trial",
            "pro_expires": 0,
            "trial_remaining": remaining,
        }
        self.accept()

    def _accept(self):
        """登录成功，关闭对话框"""
        self.accept()

    def _set_loading(self, loading: bool):
        """设置加载状态"""
        self._btn_login.setEnabled(not loading)
        self._input_user.setEnabled(not loading)
        self._input_pwd.setEnabled(not loading)
        self._chk_remember.setEnabled(not loading)

        if loading:
            self._btn_login.setText("登录中...")
        else:
            self._btn_login.setText("登  录")

    def _show_error(self, msg: str):
        """显示/隐藏错误信息"""
        if msg:
            self._lbl_error.setText(msg)
            self._lbl_error.setVisible(True)
        else:
            self._lbl_error.setText("")
            self._lbl_error.setVisible(False)

    # ============================================================
    # 公开方法
    # ============================================================

    def get_user_info(self) -> dict | None:
        """获取登录后的用户信息"""
        return self._user_info


# ============================================================
# 入口函数
# ============================================================

def show_login_dialog(parent=None) -> dict | None:
    """
    显示登录对话框，阻塞直到用户登录/跳过/关闭。

    Returns:
        用户信息字典（登录成功或试用模式），关闭窗口返回 None

        {
            "token": "eyJhbGci...",
            "username": "player1",
            "level": "basic" | "pro" | "trial",
            "pro_expires": 1735689600,
            "trial_remaining": 2,     # 仅试用模式
        }
    """
    dialog = LoginDialog(parent)
    result = dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        return dialog.get_user_info()
    return None


def check_and_login(parent=None) -> dict | None:
    """
    检查本地 Token 是否有效。
      - 有效 → 直接返回用户信息（不弹窗）
      - 无效/不存在 → 弹出登录对话框

    Returns:
        用户信息字典，取消返回 None
    """
    # 先检查本地 Token
    if is_token_available():
        data = __import__("src.security.token_store", fromlist=["load_token"]).load_token()
        if data:
            logger.info(f"[Login] 使用本地 Token (用户: {data.get('username')})")
            return {
                "token": data.get("token", ""),
                "username": data.get("username", ""),
                "level": data.get("level", "basic"),
                "pro_expires": data.get("pro_expires", 0),
            }

    # Token 无效，显示登录对话框
    return show_login_dialog(parent)
