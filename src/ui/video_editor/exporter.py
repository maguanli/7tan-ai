"""
视频剪辑器 — 导出引擎

基于 FFmpeg CLI 实现。Phase 3 基础版：
- H.264 MP4 导出（固定预设）
- 支持单视频轨 + 单音频轨 + 字幕烧录
- filter_complex 方式：trim + concat + overlay

Phase 5+ 将扩展：H.265/VP9、封面导出、纯音频导出。
"""

import subprocess
import os
import tempfile
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.video_editor.data_models import Project, ExporterConfig

from loguru import logger

from src.ui.video_editor.config import (
    FFMPEG_PATH, DEFAULT_RESOLUTION, DEFAULT_FPS,
    EXPORT_PRESETS, EXPORT_QUALITY_DEFAULT,
)
from src.ui.video_editor.data_models import Clip as ClipModel
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
        """导出视频

        Args:
            project: 项目对象
            output_path: 输出路径（.mp4）
            config: 导出配置（None=使用 bilibili 预设）
            progress_callback: 进度回调 (0.0~1.0, 状态文本)

        Returns:
            是否成功
        """
        if not project or not project.tracks:
            logger.error("导出失败: 项目为空")
            return False

        self._cancelled = False
        self._progress_callback = progress_callback

        # 默认配置
        if config is None:
            from src.ui.video_editor.data_models import ExporterConfig
            config = ExporterConfig(
                export_type="video",
                resolution=project.resolution,
                fps=project.fps,
                codec="libx264",
                bitrate="6M",
                output_format="mp4",
                preset="medium",
            )

        # 确保输出目录存在
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # 检查 FFmpeg
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"

        try:
            # 构建 filter_complex
            filter_complex, output_labels = self._build_filter_complex(project, config)

            if not filter_complex:
                logger.error("导出失败: 无可导出轨道")
                return False

            # 构建命令
            cmd = self._build_command(
                project, ffmpeg, filter_complex, output_labels,
                output_path, config,
            )

            logger.info(f"导出: {project.name} → {output_path}")
            logger.debug(f"FFmpeg 命令: {' '.join(cmd)}")

            # 执行
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            # 读取 stderr 获取进度
            total_duration = project.duration or 1.0
            for line in self._process.stderr:
                if self._cancelled:
                    self._process.terminate()
                    self._report_progress(0, "已取消")
                    return False

                # 解析 FFmpeg 进度: time=HH:MM:SS.ms
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
                # 检查文件大小
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    logger.info(f"导出完成: {output_path} ({human_readable_size(size)})")
                return True
            else:
                stderr_text = ""
                if self._process.stderr:
                    try:
                        # 重新读取全部 stderr
                        pass
                    except Exception:
                        pass
                logger.error(f"FFmpeg 退出码: {ret}")
                self._report_progress(0, f"❌ 导出失败 (退出码 {ret})")
                return False

        except FileNotFoundError:
            logger.error("FFmpeg 未找到")
            self._report_progress(0, "❌ FFmpeg 未找到，请检查 config.py 中的 FFMPEG_PATH")
            return False
        except Exception as e:
            logger.error(f"导出异常: {e}")
            self._report_progress(0, f"❌ 导出异常: {e}")
            return False

    def cancel(self):
        """取消导出"""
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            logger.info("导出已取消")

    # ==================================================================
    #  filter_complex 构建
    # ==================================================================

    def _build_filter_complex(self, project: "Project",
                               config: "ExporterConfig") -> tuple:
        """构建 FFmpeg filter_complex 字符串

        Returns:
            (filter_complex_str, {'video': label, 'audio': label})
        """
        parts = []
        inputs = []        # -i 参数列表
        input_labels = []  # 对应的标签 [0:v] 等
        input_index = 0    # 当前输入索引

        # 收集视频轨和音频轨的 Clip
        video_clips = []
        audio_clips = []
        subtitle_clips = []

        for track in project.tracks:
            for clip in track.clips:
                if isinstance(clip, ClipModel):
                    if track.type == "video":
                        video_clips.append((clip, input_index))
                        inputs.append(clip.source_path)
                        input_labels.append(f"[{input_index}:v]")
                        input_index += 1
                    elif track.type == "audio":
                        audio_clips.append((clip, input_index))
                        inputs.append(clip.source_path)
                        input_labels.append(f"[{input_index}:a]")
                        input_index += 1

        if not video_clips and not audio_clips:
            return "", {}

        # ---- 视频链：trim → setpts → concat ----
        video_labels = []
        if video_clips:
            for i, (clip, idx) in enumerate(video_clips):
                dur = clip.duration
                ss = clip.source_start
                speed = max(clip.speed, 0.01)
                label = f"v{i}"
                # trim + setpts + 变速
                parts.append(
                    f"[{idx}:v]trim=start={ss}:duration={dur},"
                    f"setpts=PTS-STARTPTS,"
                    f"setpts=PTS/{speed}"
                    f"[{label}]"
                )
                video_labels.append(label)

            if len(video_labels) == 1:
                parts.append(f"[{video_labels[0]}]format=yuv420p[vout]")
            else:
                concat_inputs = "".join(f"[{l}]" for l in video_labels)
                parts.append(
                    f"{concat_inputs}concat=n={len(video_labels)}:v=1:a=0,"
                    f"format=yuv420p[vout]"
                )

        # ---- 音频链：atrim → atempo → concat ----
        audio_labels = []
        if audio_clips:
            for i, (clip, idx) in enumerate(audio_clips):
                dur = clip.duration
                ss = clip.source_start
                speed = max(clip.speed, 0.01)
                # atempo 范围 0.5~2.0，需要链式处理极端倍速
                tempo_filters = self._build_atempo_chain(speed)
                label = f"a{i}"
                parts.append(
                    f"[{idx}:a]atrim=start={ss}:duration={dur},"
                    f"asetpts=PTS-STARTPTS"
                    f"{tempo_filters}"
                    f"[{label}]"
                )
                audio_labels.append(label)

            if len(audio_labels) == 1:
                parts.append(f"[{audio_labels[0]}]aformat=sample_fmts=fltp[aout]")
            else:
                concat_inputs = "".join(f"[{l}]" for l in audio_labels)
                parts.append(
                    f"{concat_inputs}concat=n={len(audio_labels)}:v=0:a=1,"
                    f"aformat=sample_fmts=fltp[aout]"
                )

        # ---- 字幕烧录 ----
        for track in project.tracks:
            if track.type == "subtitle":
                for sub in track.clips:
                    from src.ui.video_editor.data_models import SubtitleClip
                    if isinstance(sub, SubtitleClip):
                        subtitle_clips.append(sub)

        if subtitle_clips and video_clips:
            # 使用 drawtext 烧录字幕
            drawtext_parts = []
            for sub in subtitle_clips:
                escaped = sub.text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
                font_size = sub.font_size
                color = sub.color.lstrip("#")
                y_pos = "h-th-20" if sub.position == "bottom" else \
                        "20" if sub.position == "top" else "(h-th)/2"
                drawtext_parts.append(
                    f"drawtext=text='{escaped}':fontfile='C\\:/Windows/Fonts/msyh.ttc':"
                    f"fontsize={font_size}:fontcolor={color}:"
                    f"x=(w-tw)/2:y={y_pos}:"
                    f"enable='between(t,{sub.start_time},{sub.end_time})'"
                )

            if drawtext_parts:
                subtitle_chain = ",".join(drawtext_parts)
                parts.append(f"[vout]{subtitle_chain}[vout_sub]")
                video_label = "vout_sub"
            else:
                video_label = "vout"
        else:
            video_label = "vout" if video_clips else None

        filter_str = ";".join(parts)

        # 输出标签映射
        out_labels = {}
        if video_clips:
            out_labels["video"] = video_label or "vout"
        if audio_clips:
            out_labels["audio"] = "aout"

        return filter_str, out_labels

    def _build_atempo_chain(self, speed: float) -> str:
        """构建 atempo 链（处理任意倍速）

        atempo 单次范围 0.5~2.0。超出范围需要链式处理。
        """
        if 0.5 <= speed <= 2.0:
            return f",atempo={speed}"

        # 链式分解
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
                        output_path: str, config: "ExporterConfig") -> list:
        """构建 FFmpeg 命令行"""
        cmd = [ffmpeg, "-y"]

        # 输入文件
        inputs_seen = set()
        for track in project.tracks:
            for clip in track.clips:
                if isinstance(clip, ClipModel):
                    if clip.source_path not in inputs_seen:
                        cmd.extend(["-i", clip.source_path])
                        inputs_seen.add(clip.source_path)

        # filter_complex
        cmd.extend(["-filter_complex", filter_complex])

        # 映射
        if "video" in output_labels:
            cmd.extend(["-map", f"[{output_labels['video']}]"])
        if "audio" in output_labels:
            cmd.extend(["-map", f"[{output_labels['audio']}]"])

        # 编码参数
        if "video" in output_labels:
            cmd.extend([
                "-c:v", config.codec,
                "-preset", config.preset,
                "-b:v", config.bitrate,
                "-r", str(config.fps),
                "-s", f"{config.resolution[0]}x{config.resolution[1]}",
            ])
        if "audio" in output_labels:
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "192k",
            ])

        # 输出
        cmd.append(output_path)

        return cmd

    # ==================================================================
    #  辅助方法
    # ==================================================================

    def _parse_ffmpeg_time(self, time_str: str) -> float:
        """解析 FFmpeg time= 格式"""
        # HH:MM:SS.ms
        parts = time_str.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return float(time_str)

    def _report_progress(self, pct: float, status: str):
        """报告进度"""
        if self._progress_callback:
            try:
                self._progress_callback(pct, status)
            except Exception:
                pass

    @staticmethod
    def estimate_size(project: "Project", bitrate_mbps: float = 6.0) -> str:
        """估算导出大小"""
        dur = project.duration or 0
        bits = dur * bitrate_mbps * 1_000_000
        total_bytes = int(bits / 8 * 1.1)
        return human_readable_size(total_bytes)
