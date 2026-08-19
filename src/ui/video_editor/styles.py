"""
视频剪辑器 — 样式常量

复用 7Tan 全局主题色，扩展剪辑器专用样式。
"""

from ..theme import THEME  # noqa: F401 — 复用全局主题

# ===== 剪辑器专用颜色 =====
EDITOR_BG = "#0d1117"           # 编辑器主背景（比全局更深）
TIMELINE_BG = "#161b22"         # 时间轴背景
TRACK_BG = "#1c2128"            # 轨道背景
TRACK_ALT_BG = "#22272e"        # 轨道交替色
CLIP_VIDEO_COLOR = "#3b82f6"    # 视频片段色（蓝）
CLIP_AUDIO_COLOR = "#10b981"    # 音频片段色（绿）
CLIP_IMAGE_COLOR = "#f59e0b"    # 图片片段色（橙）
CLIP_SUBTITLE_COLOR = "#8b5cf6" # 字幕片段色（紫）
PLAYHEAD_COLOR = "#ef4444"      # 播放头色（红）
SNAP_LINE_COLOR = "#00d4ff"     # 吸附线色（青）
SELECTION_COLOR = "#00d4ff44"   # 选中高亮
RECORDING_OVERLAY_BG = "#000000aa"  # 录屏悬浮条半透明背景

# ===== 时间轴样式 =====
TIMELINE_STYLESHEET = f"""
QGraphicsView {{
    background-color: {TIMELINE_BG};
    border: 1px solid {THEME['border']};
    border-radius: 4px;
}}
"""

# ===== 素材库样式 =====
MEDIA_BIN_STYLESHEET = f"""
QListWidget {{
    background-color: {EDITOR_BG};
    border: 1px solid {THEME['border']};
    border-radius: 4px;
}}
QListWidget::item {{
    padding: 4px;
    border-radius: 4px;
}}
QListWidget::item:hover {{
    background-color: {THEME['hover']};
}}
QListWidget::item:selected {{
    background-color: {THEME['accent']}44;
}}
"""

# ===== 播放器控制栏样式 =====
PLAYER_CONTROL_STYLESHEET = f"""
QPushButton {{
    background: transparent;
    color: {THEME['text_primary']};
    border: none;
    font-size: 18px;
    padding: 6px 12px;
    border-radius: 4px;
}}
QPushButton:hover {{
    background-color: {THEME['hover']};
}}
"""

# ===== 底部工具栏样式 =====
TOOLBAR_STYLESHEET = f"""
QPushButton {{
    background-color: {THEME['bg_card']};
    color: {THEME['text_primary']};
    border: 1px solid {THEME['border']};
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    border-color: {THEME['accent']}88;
    background-color: {THEME['hover']};
}}
"""
