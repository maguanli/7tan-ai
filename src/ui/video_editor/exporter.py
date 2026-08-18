"""
视频剪辑器 — 导出引擎

基于 FFmpeg CLI 实现。
Phase 3: H.264 MP4 基础导出
Phase 6: +转场(xfade/acrossfade) + 滤镜(eq/gblur/unsharp/vignette/lut3d) + 关键帧动画
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.video_editor.data_models import Project, ExporterConfig

from loguru import logger

from src.ui.video_editor.config import (
    FFMPEG_PATH, DEFAULT_RESOLUTION, DEFAULT_FPS,
)
from src.ui.video_editor.data_models import Clip as ClipModel, SubtitleClip, FilterConfig, Transition
from src.ui.video_editor.color_filter import ColorFilterEngine
from src.ui.video_editor.transition_engine import TransitionEngine, ALL_TRANSITIONS
from src.ui.video_editor.keyframe import KeyframeManager
from src.ui.video_editor.utils import format_time, human_readable_size


class Exporter:
    """视频导出器 — 调用 FFmpeg 合成并编码"""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._cancelled: bool = False
        self._progress_callback: Optional[Callable[[float, str], None]] = None

    # ==================================================================
    #  公开 API
    # ==================================================================

    def export(self, project: "Project", output_path: str,
               config: Optional["ExporterConfig"] = None,
               progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """导出视频"""
        if not project or not project.tracks:
            logger.error("导出失败: 项目为空")
            return False

        self._cancelled = False
        self._progress_callback = progress_callback

        if config is None:
            from src.ui.video_editor.data_models import ExporterConfig
            config = ExporterConfig(
                export_type="video", resolution=project.resolution,
                fps=project.fps, codec="libx264", bitrate="6M",
                output_format="mp4", preset="medium",
            )

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"

        try:
            filter_complex, output_labels, inputs = self._build_filter_complex(project, config)
            if not filter_complex:
                logger.error("导出失败: 无可导出轨道")
                return False

            cmd = self._build_command(project, ffmpeg, filter_complex, output_labels,
                                      output_path, config, inputs)
            logger.info(f"导出: {project.name} → {output_path}")

            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            total_duration = project.duration or 1.0
            for line in self._process.stderr:
                if self._cancelled:
                    self._process.terminate()
                    self._report_progress(0, "已取消")
                    return False
                if "time=" in line:
                    t_str = line.split("time=")[1].split()[0]
                    try:
                        current = self._parse_ffmpeg_time(t_str)
                        pct = min(current / max(total_duration, 0.1), 0.99)
                        self._report_progress(pct, f"导出中… {pct*100:.0f}%")
                    except (ValueError, IndexError):
                        pass

            ret = self._process.wait()
            if ret == 0:
                self._report_progress(1.0, "✅ 导出完成")
                if os.path.exists(output_path):
                    logger.info(f"导出完成: {output_path} ({human_readable_size(os.path.getsize(output_path))})")
                return True
            else:
                logger.error(f"FFmpeg 退出码: {ret}")
                self._report_progress(0, f"❌ 导出失败 (退出码 {ret})")
                return False
        except FileNotFoundError:
            self._report_progress(0, "❌ FFmpeg 未找到")
            return False
        except Exception as e:
            logger.error(f"导出异常: {e}")
            self._report_progress(0, f"❌ 导出异常: {e}")
            return False

    def cancel(self):
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()

    # ==================================================================
    #  filter_complex 构建（Phase 6 增强版）
    # ==================================================================

    def _build_filter_complex(self, project: "Project", config: "ExporterConfig"):
        """构建 filter_complex，支持转场 + 滤镜 + 关键帧"""
        parts = []
        inputs = []
        input_index = 0

        video_clips: list[tuple] = []
        audio_clips: list[tuple] = []
        subtitle_clips: list = []

        for track in project.tracks:
            for clip in track.clips:
                if isinstance(clip, ClipModel):
                    if track.type == "video":
                        video_clips.append((clip, input_index))
                        inputs.append(clip.source_path)
                        input_index += 1
                    elif track.type == "audio":
                        audio_clips.append((clip, input_index))
                        inputs.append(clip.source_path)
                        input_index += 1
                elif isinstance(clip, SubtitleClip):
                    subtitle_clips.append(clip)

        # ---- 视频链：trim → setpts → [滤镜] → [关键帧] → [转场] ----
        if video_clips:
            # 先处理每个片段：trim + setpts + 滤镜 + 关键帧
            processed_labels = []
            for i, (clip, idx) in enumerate(video_clips):
                dur = clip.duration
                ss = clip.source_start
                speed = max(clip.speed, 0.01)
                label = f"v{i}"
                inner_label = f"v{i}trim"

                # trim + setpts + 变速
                trim_chain = (
                    f"[{idx}:v]trim=start={ss}:duration={dur},"
                    f"setpts=PTS-STARTPTS,"
                    f"setpts=PTS/{speed}"
                    f"[{inner_label}]"
                )
                parts.append(trim_chain)

                # 滤镜链
                if getattr(clip, 'filters', None) and clip.filters:
                    for fc in clip.filters:
                        if isinstance(fc, FilterConfig) and fc.enabled:
                            filtered_label = f"{label}_f"
                            filter_str = ColorFilterEngine.build_filter_string(
                                fc, inner_label, filtered_label
                            )
                            # 提取链体（去掉标签包装）
                            body = filter_str.split("]", 1)[1].rsplit("[", 1)[0] if "]" in filter_str else ""
                            if body and body != "copy":
                                parts.append(f"[{inner_label}]{body}[{filtered_label}]")
                                inner_label = filtered_label

                # 关键帧动画
                if getattr(clip, 'keyframes', None) and clip.keyframes:
                    kf_str = KeyframeManager.build_keyframe_filter(clip, inner_label, f"{label}_kf", dur)
                    if kf_str:
                        body = kf_str.split("]", 1)[1].rsplit("[", 1)[0] if "]" in kf_str else ""
                        if body:
                            parts.append(f"[{inner_label}]{body}[{label}_kf]")
                            inner_label = f"{label}_kf"

                # 重命名为最终标签
                if inner_label != label:
                    parts.append(f"[{inner_label}]copy[{label}]")

                processed_labels.append(label)

            # 转场链
            transitions = getattr(project, 'transitions', None) or []
            if len(processed_labels) >= 2:
                transition_map = {}
                for t in transitions:
                    key = (t.prev_clip_id, t.next_clip_id)
                    transition_map[key] = t

                merged_labels = []
                # 按 clip 在 video_clips 中的顺序重建
                # 简化：假设转场按相邻顺序排列
                i = 0
                while i < len(processed_labels):
                    if i < len(processed_labels) - 1:
                        clip_i = video_clips[i][0]
                        clip_j = video_clips[i + 1][0]
                        trans = transition_map.get((clip_i.id, clip_j.id))
                        if trans:
                            xfade_label = f"xfade_{i}"
                            # 计算 offset
                            offset = clip_i.effective_duration - trans.duration
                            if offset < 0:
                                offset = 0
                            xfade = TransitionEngine.build_xfade_with_offset(
                                processed_labels[i], processed_labels[i + 1],
                                trans, offset, xfade_label
                            )
                            parts.append(xfade)
                            processed_labels[i + 1] = xfade_label
                            i += 1
                            continue
                    merged_labels.append(processed_labels[i])
                    i += 1

                if len(merged_labels) == 1:
                    parts.append(f"[{merged_labels[0]}]format=yuv420p[vout]")
                else:
                    concat_inputs = "".join(f"[{l}]" for l in merged_labels)
                    parts.append(f"{concat_inputs}concat=n={len(merged_labels)}:v=1:a=0,format=yuv420p[vout]")
            elif len(processed_labels) == 1:
                parts.append(f"[{processed_labels[0]}]format=yuv420p[vout]")

        # ---- 音频链 ----
        if audio_clips:
            audio_labels = []
            for i, (clip, idx) in enumerate(audio_clips):
                dur = clip.duration
                ss = clip.source_start
                speed = max(clip.speed, 0.01)
                tempo_filters = self._build_atempo_chain(speed)
                label = f"a{i}"
                parts.append(
                    f"[{idx}:a]atrim=start={ss}:duration={dur},asetpts=PTS-STARTPTS"
                    f"{tempo_filters}[{label}]"
                )
                audio_labels.append(label)

            if len(audio_labels) == 1:
                parts.append(f"[{audio_labels[0]}]aformat=sample_fmts=fltp[aout]")
            else:
                concat_inputs = "".join(f"[{l}]" for l in audio_labels)
                parts.append(f"{concat_inputs}concat=n={len(audio_labels)}:v=0:a=1,aformat=sample_fmts=fltp[aout]")

        # ---- 字幕烧录 ----
        video_label = "vout" if video_clips else None
        if subtitle_clips and video_clips:
            drawtext_parts = []
            for sub in subtitle_clips:
                escaped = sub.text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
                y_pos = ("h-th-20" if sub.position == "bottom" else
                         "20" if sub.position == "top" else "(h-th)/2")
                drawtext_parts.append(
                    f"drawtext=text='{escaped}':fontfile='C\\:/Windows/Fonts/msyh.ttc':"
                    f"fontsize={sub.font_size}:fontcolor={sub.color.lstrip('#')}:"
                    f"x=(w-tw)/2:y={y_pos}:"
                    f"enable='between(t,{sub.start_time},{sub.end_time})'"
                )
            if drawtext_parts:
                parts.append(f"[{video_label}]{','.join(drawtext_parts)}[vout_sub]")
                video_label = "vout_sub"

        filter_str = ";".join(parts)
        out_labels = {}
        if video_clips:
            out_labels["video"] = video_label or "vout"
        if audio_clips:
            out_labels["audio"] = "aout"

        return filter_str, out_labels, inputs

    def _build_atempo_chain(self, speed: float) -> str:
        if 0.5 <= speed <= 2.0:
            return f",atempo={speed}"
        chain = ""
        remaining = speed
        while remaining > 2.0:
            chain += ",atempo=2.0"
            remaining /= 2.0
        while remaining < 0.5:
            chain += ",atempo=0.5"
            remaining /= 0.5
        if 0.5 <= remaining <= 2.0:
            chain += f",atempo={remaining}"
        return chain

    # ==================================================================
    #  命令构建
    # ==================================================================

    def _build_command(self, project: "Project", ffmpeg: str,
                        filter_complex: str, output_labels: dict,
                        output_path: str, config: "ExporterConfig",
                        inputs: list) -> list:
        cmd = [ffmpeg, "-y"]
        for inp in inputs:
            cmd.extend(["-i", inp])
        cmd.extend(["-filter_complex", filter_complex])
        if "video" in output_labels:
            cmd.extend(["-map", f"[{output_labels['video']}]"])
        if "audio" in output_labels:
            cmd.extend(["-map", f"[{output_labels['audio']}]"])
        if "video" in output_labels:
            cmd.extend([
                "-c:v", config.codec, "-preset", config.preset,
                "-b:v", config.bitrate, "-r", str(config.fps),
                "-s", f"{config.resolution[0]}x{config.resolution[1]}",
            ])
        if "audio" in output_labels:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        cmd.append(output_path)
        return cmd

    def _parse_ffmpeg_time(self, time_str: str) -> float:
        parts = time_str.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return float(time_str)

    def _report_progress(self, pct: float, status: str):
        if self._progress_callback:
            try:
                self._progress_callback(pct, status)
            except Exception:
                pass

    @staticmethod
    def estimate_size(project: "Project", bitrate_mbps: float = 6.0) -> str:
        dur = project.duration or 0
        bits = dur * bitrate_mbps * 1_000_000
        return human_readable_size(int(bits / 8 * 1.1))
