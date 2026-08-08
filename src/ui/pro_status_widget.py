"""
完整版状态组件
显示在侧边栏底部：当前等级、到期时间、刷新/续费按钮。

安全原则：先验证后信任。RSA 验签优先，HMAC 次之，不信任裸 level 字段。
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

from ..security.license_verify import verify_license, LicenseError
from ..security.auth_client import refresh_token
from ..security.token_store import load_token, save_token, clear_token
from ..tools.registry import invalidate_pro_cache
from ..core.score import auto_evaluate, format_score_brief
from .theme import THEME


class ProStatusWidget(QFrame):
    """完整版状态指示器（侧边栏底部）"""

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

        # 只显示用户名（账号信息），不显示 [PRO]/[免费] 等级徽章
        level_layout.addWidget(self._level_text, 1)
        layout.addLayout(level_layout)

        # --- 第二行：到期时间（仅完整版可见）---
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
        """根据当前状态刷新界面。
        
        安全原则：先验证后信任。
        1. RSA 验签 pro_license（最高优先级，不可伪造）
        2. HMAC 验证通过 + JWT level（次优先级，仅当 RSA 不可用时）
        3. 都不通过 → free
        """
        level = "free"
        pro_expires = 0
        rsa_verified = False

        token_data = load_token()
        if token_data:
            # ── 第1层：RSA 验签 pro_license（最高信任级）──
            pro_license = token_data.get("pro_license") or ""
            if pro_license:
                try:
                    result = verify_license(pro_license)
                    if result.get("level") == "pro":
                        level = "pro"
                        pro_expires = result.get("pro_expires", 0)
                        rsa_verified = True
                        logger.debug("[ProStatus] ✅ RSA 验签通过")
                except LicenseError as e:
                    err_str = str(e).lower()
                    if "公钥缺失" in err_str or "公钥未配置" in err_str:
                        logger.warning("[ProStatus] RSA 公钥缺失，无法验证授权")
                    elif "过期" in err_str:
                        logger.info(f"[ProStatus] PRO 已过期: {e}")
                    else:
                        logger.warning(f"[ProStatus] 授权验证失败: {e}")

            # ── 第2层：HMAC + stored level（仅当 RSA 未通过时使用）──
            if not rsa_verified:
                hmac_ok = token_data.get("_hmac_ok", False)
                stored_level = token_data.get("level", "free")
                stored_expires = token_data.get("pro_expires", 0)

                now = int(time.time())
                if hmac_ok and stored_level == "pro" and stored_expires > now:
                    # HMAC 通过 + level=pro + 未过期，但无 RSA 验证
                    # 可能是旧版登录（无 pro_license），信任但降级标记
                    level = "pro"
                    pro_expires = stored_expires
                    logger.debug("[ProStatus] ⚠️ HMAC 通过但无 RSA 验证，使用存储值")
                elif hmac_ok and stored_level == "pro" and stored_expires > 0:
                    # HMAC 通过但 pro 已过期 → 降级为免费
                    logger.info(f"[ProStatus] PRO 已过期 ({datetime.fromtimestamp(stored_expires).strftime('%Y-%m-%d')})，降级为免费版")
                    level = "free"
                    pro_expires = 0
                else:
                    level = "free"
                    pro_expires = 0

        # 同时检查 _user_info（外部传入的 info）
        if not rsa_verified and self._user_info.get("level") == "pro":
            ui_pro_expires = self._user_info.get("pro_expires", 0)
            if ui_pro_expires > pro_expires:
                pro_expires = ui_pro_expires
            level = "pro"

        now_ts = int(time.time())
        is_pro = (level == "pro" and pro_expires > now_ts)

        if is_pro:
            self._level_badge.setText("[PRO]")
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
            username = token_data.get("username", "") if token_data else ""
            if not username:
                username = self._user_info.get("username", "")
            self._level_text.setText(f"👤 {username}" if username else "👤 未登录")

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
            # 到期时间已按需求隐藏：不加入布局 + 不 setVisible(True)，
            # 否则无父 QLabel 会弹成独立小窗口（PRO 用户启动时必现）
            self._expiry_label.setVisible(False)
        else:
            self._level_badge.setText("[免费]")
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
            username = token_data.get("username", "") if token_data else ""
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
            logger.debug(f"[ProStatus] 评分计算失败: {e}")
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
                    invalidate_pro_cache()
                    self._user_info = {}
                    self._update_display()
                    self.logout_requested.emit()
            else:
                QMessageBox.warning(self, "刷新失败", msg)

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
        invalidate_pro_cache()
        self._user_info = {}
        self._update_display()
        self.logout_requested.emit()
        logger.info("[ProStatus] 用户已退出登录")
