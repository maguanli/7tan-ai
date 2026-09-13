"""
视频剪辑器 — 关键帧动画系统 (Phase 6)

支持属性动画：
- opacity   — 透明度（0.0~1.0）
- scale_x / scale_y — 缩放
- pos_x / pos_y — 位置（像素偏移）
- rotation  — 旋转角度（度）

缓动函数：
- linear / ease_in / ease_out / ease_in_out

FFmpeg 实现方式：
- 多个关键帧之间通过 FFmpeg 的 timeline 表达式实现线性插值
- 复杂缓动用 Python 预计算每帧值，生成关键帧表达式
"""

from dataclasses import dataclass
from typing import Optional, Callable
import math

from src.ui.video_editor.data_models import Keyframe, Clip


# ==================================================================
#  缓动函数
# ==================================================================

def _ease_linear(t: float) -> float:
    return t


def _ease_in(t: float) -> float:
    return t * t


def _ease_out(t: float) -> float:
    return t * (2.0 - t)


def _ease_in_out(t: float) -> float:
    if t < 0.5:
        return 2.0 * t * t
    return -1.0 + (4.0 - 2.0 * t) * t


EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "linear": _ease_linear,
    "ease_in": _ease_in,
    "ease_out": _ease_out,
    "ease_in_out": _ease_in_out,
}


# ==================================================================
#  关键帧编辑器（数据层）
# ==================================================================

class KeyframeManager:
    """关键帧管理器 — 不涉及 UI，纯数据操作"""

    @staticmethod
    def add_keyframe(clip: Clip, time: float, property_name: str,
                      value: float, easing: str = "linear") -> Keyframe:
        """添加关键帧"""
        import uuid
        kf = Keyframe(
            id=str(uuid.uuid4())[:8],
            time=time,
            property=property_name,
            value=value,
            easing=easing,
        )
        if not hasattr(clip, 'keyframes') or clip.keyframes is None:
            clip.keyframes = []
        clip.keyframes.append(kf)
        clip.keyframes.sort(key=lambda k: k.time)
        return kf

    @staticmethod
    def remove_keyframe(clip: Clip, kf_id: str) -> bool:
        """删除关键帧"""
        if not clip.keyframes:
            return False
        for i, kf in enumerate(clip.keyframes):
            if kf.id == kf_id:
                clip.keyframes.pop(i)
                return True
        return False

    @staticmethod
    def get_value_at_time(clip: Clip, property_name: str, time: float) -> float:
        """获取某时刻的插值值"""
        if not clip.keyframes:
            return KeyframeManager._default_value(property_name)

        kfs = [k for k in clip.keyframes if k.property == property_name]
        kfs.sort(key=lambda k: k.time)

        if not kfs:
            return KeyframeManager._default_value(property_name)

        # 时间在第一个之前
        if time <= kfs[0].time:
            return kfs[0].value

        # 时间在最后一个之后
        if time >= kfs[-1].time:
            return kfs[-1].value

        # 找到两个相邻关键帧进行插值
        for i in range(len(kfs) - 1):
            k0, k1 = kfs[i], kfs[i + 1]
            if k0.time <= time <= k1.time:
                # 归一化 t
                duration = k1.time - k0.time
                if duration <= 0:
                    return k0.value
                raw_t = (time - k0.time) / duration
                # 应用缓动
                eased_t = EASING_FUNCTIONS.get(k0.easing, _ease_linear)(raw_t)
                # 线性插值
                return k0.value + (k1.value - k0.value) * eased_t

        return kfs[-1].value

    @staticmethod
    def _default_value(property_name: str) -> float:
        defaults = {
            "opacity": 1.0,
            "scale_x": 1.0,
            "scale_y": 1.0,
            "pos_x": 0.0,
            "pos_y": 0.0,
            "rotation": 0.0,
        }
        return defaults.get(property_name, 1.0)

    @staticmethod
    def get_keyframes(clip: Clip, property_name: str = "") -> list[Keyframe]:
        """获取片段的所有关键帧（可按属性筛选）"""
        if not clip.keyframes:
            return []
        if not property_name:
            return sorted(clip.keyframes, key=lambda k: k.time)
        return sorted(
            [k for k in clip.keyframes if k.property == property_name],
            key=lambda k: k.time,
        )

    # ==================================================================
    #  FFmpeg 滤镜生成
    # ==================================================================

    @staticmethod
    def build_keyframe_filter(clip: Clip, clip_label: str,
                               output_label: str = "kf_out",
                               clip_duration: float = 0.0) -> str:
        """为片段生成包含关键帧动画的 FFmpeg 滤镜链

        支持的动画：
        - opacity → format=rgba,colorchannelmixer=aa=X
        - scale → scale=w=X:h=Y（需要两个关键帧配合）
        - rotation → rotate

        注意：FFmpeg 的 timeline 只支持线性插值，
        缓动效果通过 eval=frame 自定义表达式实现。

        当前简化实现：生成一系列中间值表达式（分段线性）。
        完整缓动支持需要更多工作。

        Returns:
            FFmpeg 滤镜片段，或空字符串（无关键帧时）
        """
        if not clip.keyframes:
            return ""

        duration = clip_duration or clip.effective_duration
        if duration <= 0:
            return ""

        filters = []

        # opacity 动画
        opacity_kfs = KeyframeManager.get_keyframes(clip, "opacity")
        if len(opacity_kfs) >= 2:
            # 用 colorchannelmixer 的 aa 参数控制透明度
            expr_parts = []
            for i in range(len(opacity_kfs)):
                k = opacity_kfs[i]
                tn = k.time / duration
                expr_parts.append(f"if(lt(t,{tn}),{opacity_kfs[i-1].value if i>0 else k.value},{k.value})")
            # 简化：只用线性
            # 实际上 FFmpeg 支持 timeline 但这里我们用简单方式
            # 生成 timeline 表达式数组
            timeline_parts = []
            for k in opacity_kfs:
                timeline_parts.append(f"{k.time}:{k.value}")
            # FFmpeg 的 colorchannelmixer timeline 需要 enable 参数
            # 简化为：如果只有一个渐变（两个关键帧），用简单的线性
            if len(opacity_kfs) == 2:
                k0, k1 = opacity_kfs[0], opacity_kfs[1]
                if k0.time == 0.0 and abs(k1.time - duration) < 0.05:
                    # 全程渐变
                    filters.append(
                        f"colorchannelmixer=aa={k0.value}+(t/{duration})*({k1.value - k0.value})"
                    )
            # 多关键帧：使用 enable 链
            # （复杂场景，暂时简化）

        # scale 动画
        scale_x_kfs = KeyframeManager.get_keyframes(clip, "scale_x")
        scale_y_kfs = KeyframeManager.get_keyframes(clip, "scale_y")
        if scale_x_kfs and scale_y_kfs and len(scale_x_kfs) >= 2:
            # 简单线性 scale
            pass  # 保留扩展

        # rotation 动画
        rot_kfs = KeyframeManager.get_keyframes(clip, "rotation")
        if len(rot_kfs) >= 2:
            k0, k1 = rot_kfs[0], rot_kfs[1]
            if abs(k0.time) < 0.01 and abs(k1.time - duration) < 0.05:
                deg_per_sec = (k1.value - k0.value) / duration
                filters.append(f"rotate=a={k0.value}+t*{deg_per_sec}:ow=iw:oh=ih")

        if not filters:
            return ""

        chain = ",".join(filters)
        return f"[{clip_label}]{chain}[{output_label}]"


# ==================================================================
#  便捷工厂
# ==================================================================

def create_fade_in_keyframes(clip: Clip, duration: float = 1.0) -> list[Keyframe]:
    """创建淡入关键帧"""
    k0 = KeyframeManager.add_keyframe(clip, 0.0, "opacity", 0.0, "ease_out")
    k1 = KeyframeManager.add_keyframe(clip, duration, "opacity", 1.0, "ease_out")
    return [k0, k1]


def create_fade_out_keyframes(clip: Clip, start_offset: float = 0.0,
                               fade_duration: float = 1.0) -> list[Keyframe]:
    """创建淡出关键帧"""
    dur = clip.effective_duration
    t0 = max(0, dur - fade_duration - start_offset)
    t1 = dur - start_offset
    k0 = KeyframeManager.add_keyframe(clip, t0, "opacity", 1.0, "ease_in")
    k1 = KeyframeManager.add_keyframe(clip, t1, "opacity", 0.0, "ease_in")
    return [k0, k1]


def create_zoom_in_keyframes(clip: Clip, start_scale: float = 1.0,
                               end_scale: float = 1.15) -> list[Keyframe]:
    """创建缩放推进（Ken Burns 效果）"""
    k_sx0 = KeyframeManager.add_keyframe(clip, 0.0, "scale_x", start_scale, "linear")
    k_sy0 = KeyframeManager.add_keyframe(clip, 0.0, "scale_y", start_scale, "linear")
    dur = clip.effective_duration
    k_sx1 = KeyframeManager.add_keyframe(clip, dur, "scale_x", end_scale, "linear")
    k_sy1 = KeyframeManager.add_keyframe(clip, dur, "scale_y", end_scale, "linear")
    return [k_sx0, k_sy0, k_sx1, k_sy1]
