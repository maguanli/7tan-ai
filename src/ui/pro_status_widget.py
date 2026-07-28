"""
专业版状态组件
显示在侧边栏底部：当前等级、到期时间、刷新/续费按钮。
"""
import webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from loguru import logger

from ..security.license_verify import verify_license, LicenseError
from ..security.auth_client import refresh_token
from ..security.token_store import load_token, save_token, clear_token
from .theme import THEME


class ProStatusWidget(QFrame):
    """专业版状态指示器（侧边栏底部）"""

    # 刷新完成后通知外部
    status_updated = pyqtSignal(dict)
    # 退出登录请求
    logout_requested = pyqtSignal()

    def __init__(self, user_info: dict | None = None):
        super().__init__()
        self._user_info = user_info or {}
        self.setStyleSheet(f"""
            QFrame#proStatusFrame {{
                background-color: {THEME['bg_sidebar']};
                border-top: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        self.setObjectName("proStatusFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        # --- 第一行：等级标签 ---
        level_layout = QHBoxLayout()
        level_layout.setSpacing(6)

        self._level_badge = QLabel()
        self._level_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._level_badge.setFixedHeight(24)
        self._level_badge.setStyleSheet("""
            QLabel {
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: bold;
            }
        """)

        self._level_text = QLabel()
        self._level_text.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 12px;")

        level_layout.addWidget(self._level_badge)
        level_layout.addWidget(self._level_text, 1)
        layout.addLayout(level_layout)

        # --- 第二行：到期时间（仅专业版可见）---
        self._expiry_label = QLabel()
        self._expiry_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        self._expiry_label.setVisible(False)
        layout.addWidget(self._expiry_label)

        # --- 第三行：按钮 ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)

        self._refresh_btn = QPushButton("🔄 刷新")
        self._refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._refresh_btn.setFixedHeight(26)
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['hover']};
                color: {THEME['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {THEME['accent']};
                color: #000;
            }}
        """)
        self._refresh_btn.clicked.connect(self._on_refresh)

        self._upgrade_btn = QPushButton("⭐ 升级")
        self._upgrade_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._upgrade_btn.setFixedHeight(26)
        self._upgrade_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: #000;
                border: none;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #f0c040;
            }}
        """)
        self._upgrade_btn.clicked.connect(self._on_upgrade)

        self._logout_btn = QPushButton("🚪 退出")
        self._logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._logout_btn.setFixedHeight(26)
        self._logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #ff6b6b;
                color: #fff;
                border-color: #ff6b6b;
            }}
        """)
        self._logout_btn.clicked.connect(self._on_logout)

        btn_layout.addWidget(self._refresh_btn)
        btn_layout.addWidget(self._upgrade_btn)
        btn_layout.addWidget(self._logout_btn)
        layout.addLayout(btn_layout)

        # 初始刷新
        self._update_display()

    # ============================================================
    # 公开方法
    # ============================================================

    def update_user_info(self, user_info: dict) -> None:
        """外部更新用户信息后调用"""
        self._user_info = user_info
        self._update_display()

    # ============================================================
    # 内部逻辑
    # ============================================================

    def _update_display(self) -> None:
        """根据当前状态刷新界面"""
        level = self._user_info.get("level", "basic")
        pro_expires = self._user_info.get("pro_expires", 0)

        # 从本地 Token 补充状态（load_token 保存了服务器登录响应中的
        # level/pro_expires，比本地 verify_license 更可靠）
        token_data = load_token()
        if token_data:
            # 优先使用存储的 level（服务器登录时直接返回）
            stored_level = token_data.get("level", "")
            stored_expires = token_data.get("pro_expires", 0)
            if stored_level == "pro":
                level = "pro"
                if stored_expires > pro_expires:
                    pro_expires = stored_expires
            elif stored_level == "basic" and level != "pro":
                level = "basic"
            # 本地 RSA 验签二次确认（只升级不降级）
            try:
                result = verify_license(token_data.get("token", ""))
                if result.get("level") == "pro":
                    level = "pro"
                    pro_expires = result.get("expires_at", pro_expires)
            except LicenseError:
                pass
        is_pro = (level == "pro" and pro_expires > 0)

        if is_pro:
            self._level_badge.setText("PRO")
            self._level_badge.setStyleSheet("""
                QLabel {
                    background-color: #f0c040;
                    color: #000;
                    border-radius: 4px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            self._level_text.setText("专业版")

            # 到期时间
            if pro_expires:
                dt = datetime.fromtimestamp(pro_expires)
                days_left = (dt - datetime.now()).days
                if days_left <= 0:
                    self._expiry_label.setText("⚠️ 已过期")
                    self._expiry_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")
                elif days_left <= 30:
                    self._expiry_label.setText(f"📅 {dt.strftime('%Y-%m-%d')} 到期（剩 {days_left} 天）")
                    self._expiry_label.setStyleSheet("color: #ffa94d; font-size: 11px;")
                else:
                    self._expiry_label.setText(f"📅 {dt.strftime('%Y-%m-%d')} 到期")
                    self._expiry_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
            self._expiry_label.setVisible(True)
            self._upgrade_btn.setText("⭐ 续费")
        else:
            self._level_badge.setText("基础")
            self._level_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {THEME['hover']};
                    color: {THEME['text_secondary']};
                    border-radius: 4px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
            self._level_text.setText("基础版")
            self._expiry_label.setVisible(False)
            self._upgrade_btn.setText("⭐ 专业版")

    def _on_refresh(self) -> None:
        """刷新 Token 状态"""
        token_data = load_token()
        if not token_data or not token_data.get("token"):
            QMessageBox.warning(self, "刷新失败", "未找到登录信息，请重新登录。")
            return

        try:
            result = refresh_token(token_data["token"])
        except Exception as e:
            QMessageBox.warning(self, "网络错误", f"刷新失败: {e}")
            return

        if result.get("success"):
            # 更新本地 Token
            new_token = result.get("token", token_data["token"])
            new_info = {
                **token_data,
                "token": new_token,
                "level": result.get("level", token_data.get("level", "basic")),
                "pro_expires": result.get("pro_expires", token_data.get("pro_expires", 0)),
            }
            save_token(
                token=new_info["token"],
                username=new_info.get("username", ""),
                level=new_info.get("level", "basic"),
                pro_expires=new_info.get("pro_expires", 0),
                expires_in=new_info.get("expires_in", 2592000),
            )
            self._user_info.update(new_info)
            self._update_display()
            self.status_updated.emit(new_info)
            QMessageBox.information(self, "刷新成功", "会员状态已更新！")
            logger.info("[ProStatus] Token 刷新成功")
        else:
            msg = result.get("message", "未知错误，请检查网络后重试。")
            if "401" in msg or "Token" in msg:
                reply = QMessageBox.question(
                    self, "刷新失败 — 需要重新登录",
                    f"{msg}\n\n是否清除本地登录信息并重新登录？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    clear_token()
                    self._user_info = {}
                    self._update_display()
                    self.logout_requested.emit()
            else:
                QMessageBox.warning(self, "刷新失败", msg)

    def _on_upgrade(self) -> None:
        """打开 7tan.com 升级专业版页面"""
        url = "https://www.7tan.com/pro.php"
        webbrowser.open(url)
        logger.info("[ProStatus] 打开升级页面: www.7tan.com/pro.php")

    def _on_logout(self) -> None:
        """退出会员登录"""
        reply = QMessageBox.question(
            self, "退出登录", "确定要退出当前会员账号吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        clear_token()
        self._user_info = {}
        self._update_display()
        self.logout_requested.emit()
        logger.info("[ProStatus] 用户已退出登录")
