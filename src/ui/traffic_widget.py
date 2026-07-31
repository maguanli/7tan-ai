"""
流量统计侧边栏组件

参考泼猴编译神器管理后台 apktool_stats.php 的统计指标:
  - 📊 每日活跃设备
  - 📱 新增设备
  - 🔄 回头客
  - 📈 版本分布

客户端仅做上报 + 展示入口，详细统计在管理后台查看。
"""
import webbrowser

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor

from loguru import logger

from ..config.loader import load_config
from .theme import THEME


class TrafficWidget(QFrame):
    """流量统计器（侧边栏）— 轻量展示 + 跳转管理后台"""

    # 点击查看详细统计
    view_stats_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("trafficWidget")
        self.setStyleSheet(f"""
            QFrame#trafficWidget {{
                background-color: {THEME['bg_sidebar']};
                border-top: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 6)
        layout.setSpacing(4)

        # ── 标题行 ──
        header = QHBoxLayout()
        header.setSpacing(6)

        title = QLabel("📊 流量统计")
        title.setStyleSheet(
            f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;"
        )
        title.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 查看详情按钮
        self._view_btn = QPushButton("查看")
        self._view_btn.setFixedHeight(20)
        self._view_btn.setFixedWidth(40)
        self._view_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._view_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['hover']};
                color: {THEME['text_secondary']};
                border: none;
                border-radius: 3px;
                font-size: 9px;
            }}
            QPushButton:hover {{
                background-color: {THEME['accent']};
                color: #000;
            }}
        """)
        self._view_btn.clicked.connect(self._open_stats_page)

        header.addWidget(title)
        header.addWidget(self._view_btn)
        header.addStretch()
        layout.addLayout(header)

        # ── 状态标签 ──
        self._status_label = QLabel("已上报 ✓")
        self._status_label.setStyleSheet(
            f"color: {THEME['text_muted']}; font-size: 10px;"
        )
        layout.addWidget(self._status_label)

        # ── 提示 ──
        hint = QLabel("点击查看完整统计 →")
        hint.setStyleSheet(
            f"color: {THEME['text_muted']}; font-size: 9px; font-style: italic;"
        )
        layout.addWidget(hint)

    def _open_stats_page(self):
        """打开管理后台流量统计页面"""
        config = load_config()
        base_url = config.get("site_7tan", {}).get("base_url", "https://img.7tan.cn")
        if "/api" in base_url:
            base_url = base_url.split("/api")[0]

        stats_url = f"{base_url}/7tan_stats.php"
        logger.info(f"[TrafficWidget] 打开统计页面: {stats_url}")
        webbrowser.open(stats_url)
        self.view_stats_requested.emit()

    def set_reported(self, success: bool = True):
        """更新上报状态"""
        if success:
            self._status_label.setText("已上报 ✓")
            self._status_label.setStyleSheet(
                f"color: #4caf50; font-size: 10px;"
            )
        else:
            self._status_label.setText("上报失败 ⚠")
            self._status_label.setStyleSheet(
                f"color: #ff9800; font-size: 10px;"
            )

    def mousePressEvent(self, event):
        """点击整个区域打开统计页面"""
        self._open_stats_page()
        super().mousePressEvent(event)
