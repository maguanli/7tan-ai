"""
视频剪辑器 — 素材库面板

可导入/预览/拖拽视频、音频、图片素材。
拖入素材后自动生成缩略图，支持分类筛选。

Phase 2: 缩略图列表 + 导入 + 拖拽到时间轴
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QFrame,
    QToolButton, QMenu, QComboBox,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QFont, QDrag

from loguru import logger

from src.ui.video_editor.config import (
    MEDIA_BIN_THUMBNAIL_SIZE, FFMPEG_PATH,
    MEDIA_BIN_SUPPORTED_VIDEO, MEDIA_BIN_SUPPORTED_AUDIO, MEDIA_BIN_SUPPORTED_IMAGE,
)
from src.ui.video_editor.styles import MEDIA_BIN_STYLESHEET, EDITOR_BG, THEME
from src.ui.video_editor.utils import (
    get_media_type, get_media_duration_ffprobe, generate_clip_id,
    human_readable_size, format_time,
)


class MediaBin(QWidget):
    """素材库面板

    信号：
        media_selected(dict)     — 用户点击选中素材
        media_double_clicked(dict) — 双击添加到时间轴
        media_imported(list)     — 新素材导入完成
    """

    media_selected = pyqtSignal(dict)
    media_double_clicked = pyqtSignal(dict)
    media_imported = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._media_items: dict[str, dict] = {}  # id → info
        self._thumb_cache_dir = Path("data/video_editor/thumbs")
        self._thumb_cache_dir.mkdir(parents=True, exist_ok=True)
        self._filter_type: str = "all"  # all / video / audio / image
        self._setup_ui()

    # ==================================================================
    #  UI 构建
    # ==================================================================

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ---- 标题栏 ----
        header = QHBoxLayout()
        title = QLabel("📁 素材库")
        title.setStyleSheet(
            f"color:{THEME['accent']}; font-weight:bold; font-size:14px; padding:4px;"
        )
        header.addWidget(title)
        header.addStretch()

        # 筛选下拉
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["全部", "🎬 视频", "🎵 音频", "🖼️ 图片"])
        self._filter_combo.setStyleSheet(f"""
            QComboBox {{
                background:{THEME['bg_input']}; color:{THEME['text_primary']};
                border:1px solid {THEME['border']}; border-radius:4px;
                padding:2px 8px; font-size:11px; max-width:90px;
            }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{
                background:{THEME['bg_input']}; color:{THEME['text_primary']};
                selection-background-color:{THEME['accent']}44;
            }}
        """)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        header.addWidget(self._filter_combo)
        layout.addLayout(header)

        # ---- 素材列表 ----
        self._list = QListWidget()
        self._list.setIconSize(QSize(MEDIA_BIN_THUMBNAIL_SIZE, 68))
        self._list.setSpacing(2)
        self._list.setStyleSheet(MEDIA_BIN_STYLESHEET)
        self._list.setDragEnabled(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list, 1)

        # ---- 底部按钮栏 ----
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        btn_style = f"""
            QPushButton {{
                background:{THEME['bg_card']}; color:{THEME['text_primary']};
                border:1px solid {THEME['border']}; border-radius:4px;
                padding:6px 12px; font-size:12px;
            }}
            QPushButton:hover {{ border-color:{THEME['accent']}88; }}
        """

        btn_import = QPushButton("📥 导入")
        btn_import.setStyleSheet(btn_style)
        btn_import.clicked.connect(self._on_import_clicked)
        btn_bar.addWidget(btn_import)

        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.setStyleSheet(btn_style)
        btn_refresh.clicked.connect(self._on_refresh)
        btn_bar.addWidget(btn_refresh)

        btn_bar.addStretch()

        self._count_label = QLabel("0 个素材")
        self._count_label.setStyleSheet(f"color:{THEME['text_muted']}; font-size:11px;")
        btn_bar.addWidget(self._count_label)

        layout.addLayout(btn_bar)

    # ==================================================================
    #  公开 API
    # ==================================================================

    def add_media(self, file_path: str) -> Optional[dict]:
        """添加一个媒体文件到素材库。返回 info dict 或 None。"""
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return None

        # 去重
        for info in self._media_items.values():
            if os.path.normcase(os.path.abspath(info["path"])) == \
               os.path.normcase(os.path.abspath(file_path)):
                logger.debug(f"素材已存在: {Path(file_path).name}")
                return info

        media_type = get_media_type(file_path)
        if media_type == "unknown":
            logger.warning(f"不支持的格式: {file_path}")
            return None

        info = {
            "id": generate_clip_id(),
            "path": file_path,
            "name": os.path.basename(file_path),
            "type": media_type,
            "duration": get_media_duration_ffprobe(file_path) or 0.0,
            "size": human_readable_size(os.path.getsize(file_path)),
            "thumb_path": self._generate_thumbnail(file_path),
        }
        self._media_items[info["id"]] = info
        self._add_to_list(info)
        self._update_count()
        return info

    def add_media_batch(self, file_paths: list[str]) -> list[dict]:
        """批量导入"""
        results = []
        for fp in file_paths:
            r = self.add_media(fp)
            if r:
                results.append(r)
        if results:
            self.media_imported.emit(results)
        return results

    def remove_media(self, media_id: str):
        """移除素材"""
        if media_id in self._media_items:
            del self._media_items[media_id]
            self._rebuild_list()
            self._update_count()

    def get_selected(self) -> list[dict]:
        """获取当前选中的素材 info"""
        result = []
        for item in self._list.selectedItems():
            info = item.data(Qt.ItemDataRole.UserRole)
            if info:
                result.append(info)
        return result

    def get_all_media(self) -> list[dict]:
        """获取全部素材"""
        return list(self._media_items.values())

    def clear(self):
        """清空素材库"""
        self._media_items.clear()
        self._list.clear()
        self._update_count()

    def refresh(self):
        """刷新素材库（录屏完成后调用）"""
        self._rebuild_list()

    # ==================================================================
    #  内部方法
    # ==================================================================

    def _add_to_list(self, info: dict):
        """添加一项到列表（受筛选影响）"""
        if not self._pass_filter(info):
            return

        icon = {"video": "🎬", "audio": "🎵", "image": "🖼️"}.get(info["type"], "📄")
        dur_str = format_time(info["duration"]) if info["duration"] > 0 else "--:--"
        label = f"{icon} {info['name']}\n   {dur_str}  |  {info.get('size', '?')}"

        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, info)
        item.setToolTip(f"{info['path']}\n时长: {dur_str}\n大小: {info.get('size', '?')}")

        # 缩略图
        thumb_path = info.get("thumb_path", "")
        if thumb_path and os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
            if not pix.isNull():
                pix = pix.scaled(
                    MEDIA_BIN_THUMBNAIL_SIZE, 68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                item.setIcon(QIcon(pix))

        self._list.addItem(item)

    def _rebuild_list(self):
        """根据筛选重建列表"""
        self._list.clear()
        for info in self._media_items.values():
            self._add_to_list(info)

    def _pass_filter(self, info: dict) -> bool:
        if self._filter_type == "all":
            return True
        return info.get("type") == self._filter_type

    def _update_count(self):
        total = len(self._media_items)
        self._count_label.setText(f"{total} 个素材")

    def _generate_thumbnail(self, file_path: str) -> str:
        """用 FFmpeg 生成缩略图"""
        media_type = get_media_type(file_path)
        if media_type not in ("video", "image"):
            return ""

        out_name = f"{generate_clip_id()}.jpg"
        out_path = self._thumb_cache_dir / out_name

        if out_path.exists():
            return str(out_path)

        if not FFMPEG_PATH.exists():
            return ""

        try:
            if media_type == "video":
                # 取第 2 秒的一帧
                subprocess.run(
                    [str(FFMPEG_PATH), "-y", "-ss", "2", "-i", file_path,
                     "-vframes", "1", "-q:v", "3",
                     "-vf", f"scale={MEDIA_BIN_THUMBNAIL_SIZE}:-1",
                     str(out_path)],
                    capture_output=True, timeout=15,
                )
            elif media_type == "image":
                # 直接缩放
                subprocess.run(
                    [str(FFMPEG_PATH), "-y", "-i", file_path,
                     "-vf", f"scale={MEDIA_BIN_THUMBNAIL_SIZE}:-1",
                     str(out_path)],
                    capture_output=True, timeout=10,
                )

            if out_path.exists():
                return str(out_path)
        except Exception as e:
            logger.error(f"缩略图生成失败: {file_path} — {e}")

        return ""

    # ==================================================================
    #  事件处理
    # ==================================================================

    def _on_import_clicked(self):
        """导入按钮"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "导入素材", "",
            "媒体文件 (*.mp4 *.mov *.mkv *.avi *.mp3 *.wav *.png *.jpg *.jpeg *.gif);;"
            "视频 (*.mp4 *.mov *.mkv *.avi);;音频 (*.mp3 *.wav);;图片 (*.png *.jpg *.jpeg);;"
            "所有文件 (*.*)"
        )
        if files:
            self.add_media_batch(files)

    def _on_refresh(self):
        self._rebuild_list()

    def _on_filter_changed(self, index: int):
        filter_map = {0: "all", 1: "video", 2: "audio", 3: "image"}
        self._filter_type = filter_map.get(index, "all")
        self._rebuild_list()

    def _on_item_clicked(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole)
        if info:
            self.media_selected.emit(info)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole)
        if info:
            self.media_double_clicked.emit(info)

    def _on_context_menu(self, pos):
        """右键菜单"""
        item = self._list.itemAt(pos)
        if not item:
            return
        info = item.data(Qt.ItemDataRole.UserRole)
        if not info:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{THEME['bg_card']}; color:{THEME['text_primary']};
                     border:1px solid {THEME['border']}; padding:4px; }}
            QMenu::item {{ padding:6px 20px; }}
            QMenu::item:selected {{ background:{THEME['accent']}44; }}
        """)

        add_action = menu.addAction("➕ 添加到时间轴")
        add_action.triggered.connect(lambda: self.media_double_clicked.emit(info))

        menu.addSeparator()

        remove_action = menu.addAction("🗑️ 从素材库移除")
        remove_action.triggered.connect(lambda: self.remove_media(info["id"]))

        reveal_action = menu.addAction("📂 打开文件位置")
        reveal_action.triggered.connect(lambda: os.startfile(os.path.dirname(info["path"])))

        menu.exec(self._list.mapToGlobal(pos))
