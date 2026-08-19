"""
视频剪辑器 — 调色滤镜引擎 (Phase 6)

支持：
- 色彩调整（亮度/对比度/饱和度/色相/伽马）
- 模糊/锐化
- 暗角效果
- 3D LUT 加载
- 预设滤镜（电影/复古/清新/黑白/暖色/冷色）
- 实时预览 via FFmpeg eq/colorbalance/curves

FFmpeg 滤镜映射：
- brightness/contrast/saturation → eq
- hue → hue
- gamma → eq
- blur → gblur
- sharpen → unsharp
- vignette → vignette
- lut → lut3d
"""

from dataclasses import dataclass, field
from typing import Optional, Callable

from src.ui.video_editor.data_models import FilterConfig


# ==================================================================
#  预设滤镜
# ==================================================================

@dataclass
class FilterPreset:
    """预设滤镜定义"""
    name: str
    category: str                    # 电影/复古/清新/黑白/暖色/冷色/自定义
    config: FilterConfig


PRESETS: list[FilterPreset] = [
    FilterPreset("原图", "默认", FilterConfig(
        id="preset_none", type="color",
        brightness=0.0, contrast=1.0, saturation=1.0,
        hue=0.0, gamma=1.0,
    )),
    FilterPreset("电影质感", "电影", FilterConfig(
        id="preset_cinematic", type="color",
        brightness=-0.05, contrast=1.2, saturation=0.85,
        hue=0.0, gamma=1.1, vignette_strength=0.15,
    )),
    FilterPreset("复古胶片", "复古", FilterConfig(
        id="preset_vintage", type="color",
        brightness=0.05, contrast=0.9, saturation=0.7,
        hue=5.0, gamma=1.15, vignette_strength=0.25,
    )),
    FilterPreset("清新日系", "清新", FilterConfig(
        id="preset_japanese", type="color",
        brightness=0.1, contrast=0.95, saturation=1.15,
        hue=0.0, gamma=1.05,
    )),
    FilterPreset("经典黑白", "黑白", FilterConfig(
        id="preset_bw", type="color",
        brightness=0.0, contrast=1.3, saturation=0.0,
        hue=0.0, gamma=1.0,
    )),
    FilterPreset("暖色回忆", "暖色", FilterConfig(
        id="preset_warm", type="color",
        brightness=0.03, contrast=1.0, saturation=1.1,
        hue=10.0, gamma=1.05,
    )),
    FilterPreset("冷色科技", "冷色", FilterConfig(
        id="preset_cool", type="color",
        brightness=-0.02, contrast=1.05, saturation=1.0,
        hue=-8.0, gamma=1.0,
    )),
    FilterPreset("高对比", "电影", FilterConfig(
        id="preset_highcontrast", type="color",
        brightness=-0.08, contrast=1.5, saturation=0.9,
        hue=0.0, gamma=1.2,
    )),
]


# ==================================================================
#  滤镜引擎
# ==================================================================

class ColorFilterEngine:
    """调色滤镜引擎 — 生成 FFmpeg 滤镜字符串"""

    @staticmethod
    def build_filter_string(config: FilterConfig, clip_label: str,
                             output_label: str = "filtered") -> str:
        """为单个 clip 构建 FFmpeg 滤镜链

        Args:
            config: 滤镜配置
            clip_label: 输入标签（如 [v0]）
            output_label: 输出标签

        Returns:
            FFmpeg 滤镜字符串片段，如:
            [v0]eq=brightness=0.05:contrast=1.2:saturation=0.85,unsharp=3:3:0.5[v0_f]
        """
        if not config.enabled:
            return f"[{clip_label}]copy[{output_label}]"

        filters = []

        # eq 滤镜（色彩调整）
        eq_parts = []
        if abs(config.brightness) > 0.001:
            eq_parts.append(f"brightness={config.brightness:.3f}")
        if abs(config.contrast - 1.0) > 0.001:
            eq_parts.append(f"contrast={config.contrast:.3f}")
        if abs(config.saturation - 1.0) > 0.001:
            eq_parts.append(f"saturation={config.saturation:.3f}")
        if abs(config.gamma - 1.0) > 0.001:
            eq_parts.append(f"gamma={config.gamma:.3f}")
        if eq_parts:
            filters.append("eq=" + ":".join(eq_parts))

        # hue 滤镜（色相旋转）
        if abs(config.hue) > 0.001:
            filters.append(f"hue=h={config.hue}")

        # 模糊
        if config.blur_strength > 0.001:
            filters.append(f"gblur=sigma={config.blur_strength:.2f}")

        # 锐化
        if config.sharpen_strength > 0.001:
            # unsharp=lx:ly:amount
            amount = config.sharpen_strength * 5.0
            filters.append(f"unsharp=5:5:{amount:.2f}")

        # 暗角
        if config.vignette_strength > 0.001:
            # vignette=PI*angle/180: radius at which vignetting starts
            angle = config.vignette_strength * 75
            filters.append(f"vignette=PI*{angle:.1f}/180")

        # LUT
        if config.lut_path:
            # 需要用绝对路径，反斜杠转义
            escaped = config.lut_path.replace("\\", "/").replace(":", "\\:")
            filters.append(f"lut3d=file='{escaped}'")

        # 自定义
        if config.custom_filter:
            filters.append(config.custom_filter)

        if not filters:
            return f"[{clip_label}]copy[{output_label}]"

        chain = ",".join(filters)
        return f"[{clip_label}]{chain}[{output_label}]"

    @staticmethod
    def get_presets_by_category() -> dict:
        """按分类获取预设"""
        cats = {}
        for p in PRESETS:
            cats.setdefault(p.category, []).append(p)
        return cats

    @staticmethod
    def find_preset(name: str) -> Optional[FilterConfig]:
        """按名称查找预设"""
        for p in PRESETS:
            if p.name == name:
                return p.config
        return None

    # ==================================================================
    #  预览：对静态帧应用滤镜效果
    # ==================================================================

    @staticmethod
    def preview_filter(source_path: str, config: FilterConfig,
                        output_path: str, seek_time: float = 0.0) -> bool:
        """对视频某一帧应用滤镜并输出为图片

        Args:
            source_path: 源视频路径
            config: 滤镜配置
            output_path: 输出图片路径 (.png)
            seek_time: 截图时间

        Returns:
            成功
        """
        import subprocess
        import os
        from src.ui.video_editor.config import FFMPEG_PATH

        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"

        filter_str = ColorFilterEngine.build_filter_string(
            config, "0:v", "vout"
        )
        # 提取 filter 主体（去掉 [label] 标记）
        body = filter_str.split("]", 1)[1].rsplit("[", 1)[0] if "]" in filter_str else filter_str

        cmd = [
            ffmpeg, "-y",
            "-ss", str(seek_time),
            "-i", source_path,
            "-vframes", "1",
            "-vf", body,
            output_path,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=30,
            )
            return result.returncode == 0 and os.path.exists(output_path)
        except Exception:
            return False
