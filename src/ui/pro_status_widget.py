"""
账号状态组件
显示在侧边栏底部：用户名、能力值、刷新/退出按钮。

2026-09-01 起：7Tan AI 已开源，不再显示会员等级（free/pro）。
"""
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor

from loguru import logger

from ..security.auth_client import refresh_token
from ..security.token_store import load_token, save_token, clear_token
from ..tools.registry import invalidate_pro_cache
from ..core.score import auto_evaluate, format_score_brief
from .theme import THEME


class ProStatusWidget(QFrame):
    """账号状态指示器（侧边栏底部）"""

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

        # 只显示用户名（账号信息）
        level_layout.addWidget(self._level_text, 1)
        layout.addLayout(level_layout)

        # --- 第二行：到期时间（已废弃，开源后不显示）---
        self._expiry_label = QLabel()
        self._expiry_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        self._expiry_label.setVisible(False)

        # 到期时间行已按需求隐藏，不加入布局
        # layout.addWidget(self._expiry_label)

        # --- 评分行 ---
        self._score_label = QLabel()
        self._score_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        self._score_label.setVisible(False)
        # 评分行（能力值）保留显示
        layout.addWidget(self._score_label)

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
        """刷新界面：显示用户名 + 能力值。

        2026-09-01 起：7Tan AI 已开源，不再显示会员等级（free/pro）。
        """
        token_data = load_token()
        username = ""
        if token_data:
            username = token_data.get("username", "")
        if not username:
            username = self._user_info.get("username", "")
        self._level_text.setText(f"👤 {username}" if username else "👤 未登录")
        self._expiry_label.setVisible(False)

        # 更新评分
        self._update_score()

    def _update_score(self) -> None:
        """延迟异步更新评分（避免阻塞 UI）"""
        QTimer.singleShot(500, self._do_update_score)

    def _do_update_score(self) -> None:
        """实际执行评分计算并更新显示"""
        try:
            result = auto_evaluate()
            brief = format_score_brief(result)
            grade = result.get("grade", "?")
            color = result.get("grade_color", "#888")
            self._score_label.setText(f"⚡ 能力值: {brief}")
            self._score_label.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: bold; padding: 2px 0;"
            )
            self._score_label.setVisible(True)
        except Exception as e:
            logger.debug(f"[Account] 评分计算失败: {e}")
            self._score_label.setVisible(False)

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
            new_token = result.get("token", token_data["token"])
            new_info = {
                **token_data,
                "token": new_token,
                "level": result.get("level", "free"),
                "pro_expires": result.get("pro_expires", 0),
                "pro_license": result.get("pro_license") or "",
            }
            save_token(
                token=new_info["token"],
                username=new_info.get("username", ""),
                level=new_info.get("level") or "free",
                pro_expires=new_info.get("pro_expires", 0),
                expires_in=new_info.get("expires_in", 2592000),
                pro_license=new_info.get("pro_license") or "",
            )
            # 刷新后清除 Pro 门控缓存
            invalidate_pro_cache()
            self._user_info.update(new_info)
            self._update_display()
            self.status_updated.emit(new_info)
            QMessageBox.information(self, "刷新成功", "账号状态已更新！")
            logger.info("[Account] Token 刷新成功")
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
                    invalidate_pro_cache()
                    self._user_info = {}
                    self._update_display()
                    self.logout_requested.emit()
            else:
                QMessageBox.warning(self, "刷新失败", msg)

    def _on_logout(self) -> None:
        """退出登录"""
        reply = QMessageBox.question(
            self, "退出登录", "确定要退出当前账号吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        clear_token()
        invalidate_pro_cache()
        self._user_info = {}
        self._update_display()
        self.logout_requested.emit()
        logger.info("[Account] 用户已退出登录")
