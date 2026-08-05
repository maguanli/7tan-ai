"""
登录对话框
PyQt6 原生控件，精美渐变色设计。

功能:
  - 用户名/手机号 + 密码登录
  - 记住30天
  - 忘记密码 → 跳转 7tan.com
  - 错误提示
  - 登录中加载状态
  - 新用户赠送 3 次免费 AI 试用（服务端计次，防羊毛）
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QApplication,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QLinearGradient,
    QBrush, QPainter, QDesktopServices,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect,
    QPoint, pyqtSignal, QSize, QUrl,
)

from loguru import logger

from ..security.auth_client import login, LoginFailed, NetworkError, ServerError
from ..security.token_store import save_token, is_token_available
from ..security.device_fingerprint import on_login as device_fp_on_login

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

        # 设置任务栏图标（优先用 app.ico，回退到 PNG）
        icon_path = Path(__file__).parent.parent.parent / "data" / "logo" / "app.ico"
        if not icon_path.exists():
            icon_path = Path(__file__).parent.parent.parent / "data" / "logo" / "logo_v4_256.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setFixedSize(420, 525)
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
        self._card.setFixedSize(420, 525)

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

        # LOGO 图标（加载 7Tan PNG 图标）
        logo_label = QLabel()
        logo_label.setFixedSize(32, 32)
        logo_path = Path(__file__).parent.parent.parent / "data" / "logo" / "logo_v4_256.png"
        if logo_path.exists():
            logo_label.setPixmap(QPixmap(str(logo_path)).scaled(
                32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        else:
            logo_label.setText("🎮")
            logo_label.setFont(QFont("Segoe UI Emoji", 28))
        title_bar.addWidget(logo_label)

        title_bar.addStretch()

        # 关闭按钮
        btn_close = QPushButton("X")
        btn_close.setObjectName("btnClose")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self._btn_toggle_pwd.setFixedSize(44, 42)
        self._btn_toggle_pwd.setToolTip("显示/隐藏密码")
        self._btn_toggle_pwd.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_toggle_pwd.clicked.connect(self._toggle_password)
        pwd_row.addWidget(self._btn_toggle_pwd)

        layout.addLayout(pwd_row)
        layout.addSpacing(12)

        # --- 记住密码 + 忘记密码 ---
        bottom_row = QHBoxLayout()

        self._chk_remember = QCheckBox("记住 30 天")
        self._chk_remember.setFont(QFont("Microsoft YaHei", 11))
        self._chk_remember.setChecked(True)
        self._chk_remember.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_row.addWidget(self._chk_remember)

        bottom_row.addStretch()

        btn_forgot = QPushButton("忘记密码？")
        btn_forgot.setObjectName("btnLink")
        btn_forgot.setFont(QFont("Microsoft YaHei", 11))
        btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_forgot.clicked.connect(self._on_forgot_password)
        bottom_row.addWidget(btn_forgot)

        layout.addLayout(bottom_row)
        layout.addSpacing(8)

        # --- 协议同意（用户协议 + 隐私政策） ---
        agree_row = QHBoxLayout()
        agree_row.setSpacing(0)

        self._chk_agree = QCheckBox("我已阅读并同意")
        self._chk_agree.setFont(QFont("Microsoft YaHei", 10))
        self._chk_agree.setChecked(False)  # 必须主动勾选才可登录（合规）
        self._chk_agree.setCursor(Qt.CursorShape.PointingHandCursor)
        agree_row.addWidget(self._chk_agree)

        from src.config.loader import load_config as _load_cfg_agree
        _cfg_agree = _load_cfg_agree()
        _base_agree = _cfg_agree.get("site_7tan", {}).get("base_url", "")
        _site_root_agree = _base_agree.replace("/api", "") if _base_agree else "https://www.7tan.com"
        _site_root_agree = _site_root_agree.replace("img.7tan.cn", "www.7tan.com")
        _url_agreement = _site_root_agree + "/agreement.php"
        _url_privacy = _site_root_agree + "/privacy.php"

        btn_agreement = QPushButton("《用户协议》")
        btn_agreement.setObjectName("btnAgreeLink")
        btn_agreement.setFont(QFont("Microsoft YaHei", 10))
        btn_agreement.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_agreement.setToolTip(_url_agreement)
        btn_agreement.clicked.connect(lambda: self._open_url(_url_agreement))
        agree_row.addWidget(btn_agreement)

        lbl_and = QLabel("和")
        lbl_and.setFont(QFont("Microsoft YaHei", 10))
        lbl_and.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        agree_row.addWidget(lbl_and)

        btn_privacy = QPushButton("《隐私政策》")
        btn_privacy.setObjectName("btnAgreeLink")
        btn_privacy.setFont(QFont("Microsoft YaHei", 10))
        btn_privacy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_privacy.setToolTip(_url_privacy)
        btn_privacy.clicked.connect(lambda: self._open_url(_url_privacy))
        agree_row.addWidget(btn_privacy)

        agree_row.addStretch()
        layout.addLayout(agree_row)
        layout.addSpacing(12)

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

        layout.addStretch()

        # --- 底部 ---
        footer = QPushButton("没有账号？访问 7tan.com 注册")
        footer.setObjectName("btnLink")
        footer.setFont(QFont("Microsoft YaHei", 10))
        footer.setCursor(Qt.CursorShape.PointingHandCursor)
        from src.config.loader import load_config as _load_cfg5
        _cfg5 = _load_cfg5()
        _base5 = _cfg5.get("site_7tan", {}).get("base_url", "")
        _site_root5 = _base5.replace("/api", "") if _base5 else "https://www.7tan.com"
        _site_root5 = _site_root5.replace("img.7tan.cn", "www.7tan.com")
        footer.clicked.connect(lambda: self._open_url(_site_root5 + "/bbs/register.php"))
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
                background: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                font-size: 13px;
                font-weight: bold;
                border-radius: 15px;
                text-align: center;
                padding: 0 0 1px 0;
            }}
            #btnClose:hover {{
                background: #e81123;
                color: #ffffff;
                border-color: #e81123;
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
            #btnAgreeLink {{
                background: transparent;
                color: {ACCENT};
                border: none;
                text-decoration: underline;
                padding: 0 2px;
                font-size: 10px;
            }}
            #btnAgreeLink:hover {{
                color: {ACCENT_HOVER};
            }}
            #btnTogglePwd {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 18px;
                border-radius: 0 8px 8px 0;
                padding: 0;
            }}
            #btnTogglePwd:hover {{
                background-color: rgba(255,255,255,0.08);
                color: {TEXT_PRIMARY};
            }}
            QCheckBox {{
                color: {TEXT_SECONDARY};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {BORDER};
                border-radius: 4px;
                background: transparent;
            }}
            QCheckBox::indicator:hover {{
                border-color: {ACCENT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT};
                border-color: {ACCENT};
            }}
            QCheckBox:checked {{
                color: {TEXT_PRIMARY};
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
        """在系统默认浏览器中打开 URL（三级兜底：QDesktopServices → webbrowser → os.startfile）"""
        try:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            if QDesktopServices.openUrl(QUrl(url)):
                return
        except Exception as _e:
            logger.debug("[Login] QDesktopServices 打开失败: " + str(_e))
        try:
            import webbrowser
            if webbrowser.open(url):
                return
        except Exception as _e:
            logger.debug("[Login] webbrowser 打开失败: " + str(_e))
        try:
            import os
            os.startfile(url)  # Windows ShellExecute，管理员权限下也可靠
        except Exception as _e:
            logger.error("[Login] 打开 URL 失败: " + url + " -> " + str(_e))
            self._show_error("无法打开浏览器，请手动访问: " + url)

    def _on_forgot_password(self):
        """忘记密码 → 打开 7tan.com 找回密码页面"""
        try:
            from src.config.loader import load_config as _load_cfg6
            _cfg6 = _load_cfg6()
            _base6 = _cfg6.get("site_7tan", dict()).get("base_url", "") if _cfg6 else ""
            _site_root6 = _base6.replace("/api", "") if _base6 else "https://www.7tan.com"
            _site_root6 = _site_root6.replace("img.7tan.cn", "www.7tan.com")
            _url6 = _site_root6 + "/bbs/77562/"
            logger.info("[Login] 忘记密码 -> " + _url6)
            self._open_url(_url6)
        except Exception as _e:
            logger.error("[Login] 忘记密码跳转异常: " + str(_e))
            self._open_url("https://www.7tan.com/bbs/77562/")  # 兜底直连官网
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

        # 协议同意校验
        if not self._chk_agree.isChecked():
            self._show_error("请先阅读并同意《用户协议》和《隐私政策》")
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

            # 保存 Token（含试用次数）
            save_token(
                token=result.get("token") or "",
                username=result.get("username") or "",
                level=result.get("level") or "free",
                pro_expires=result.get("pro_expires", 0),
                expires_in=result.get("expires_in", 2592000),
                trial_ai_count=result.get("trial_ai_count", 0),
                pro_license=result.get("pro_license") or "",
            )

            self._user_info = result
            logger.info(f"[Login] 登录成功: {result['username']} (等级: {result['level']})")

            # 设备指纹：本地烙印记 + 服务器多设备检测（静默，不阻塞）
            try:
                device_fp_on_login(result)
            except Exception as _fp_err:
                logger.debug(f"[Login] 设备指纹处理异常: {_fp_err}")

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
    显示登录对话框，阻塞直到用户登录或关闭。

    Returns:
        用户信息字典，关闭窗口返回 None

        {
            "token": "eyJhbGci...",
            "username": "player1",
            "level": "free" | "pro",
            "pro_expires": 1735689600,
            "trial_ai_count": 3,     # AI 试用剩余次数
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
            _info = {
                "token": data.get("token", ""),
                "username": data.get("username", ""),
                "level": data.get("level", "free"),
                "pro_expires": data.get("pro_expires", 0),
            }
            # 设备指纹：本地烙印记 + 服务器多设备检测（静默）
            try:
                device_fp_on_login(_info)
            except Exception as _fp_err:
                logger.debug(f"[Login] 设备指纹处理异常: {_fp_err}")
            return _info

    # Token 无效，显示登录对话框
    return show_login_dialog(parent)
