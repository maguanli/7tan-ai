"""
AI 字幕引擎 — 语音识别 + 字幕生成

Phase 5: whisper.cpp 本地识别 (优先) + Google Speech 在线降级
SRT/VTT 输出 → SubtitleClip 模型 → 时间轴字幕轨

架构：
  音频 → 语音识别 → 时间轴文本 → SubtitleClip 列表 → 字幕轨
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
import json
import threading
import re
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal
from loguru import logger


# ======================================================================
#  字幕引擎
# ======================================================================

class AISubtitleEngine(QObject):
    """AI 字幕引擎

    使用方式:
        engine = AISubtitleEngine()
        engine.progress.connect(on_progress)
        engine.finished.connect(on_finished)  # → list[SubtitleClip]

        engine.generate_from_audio("audio.wav")
        # 或
        engine.generate_from_video("video.mp4")
    """

    progress = pyqtSignal(str)               # 进度消息
    finished = pyqtSignal(list)              # list[dict] → SubtitleClip 数据
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cancelled = False
        self._thread: Optional[threading.Thread] = None

        # whisper 配置
        self.whisper_model: str = "medium"    # tiny / base / small / medium / large
        self.whisper_path: str = ""           # whisper.cpp 可执行路径，空=自动查找
        self.language: str = "zh"             # 识别语言

    # ==================================================================
    #  公开接口
    # ==================================================================

    def generate_from_video(self, video_path: str) -> None:
        """从视频文件提取音频并识别字幕"""
        self._cancelled = False
        self._thread = threading.Thread(
            target=self._run_video, args=(video_path,), daemon=True
        )
        self._thread.start()

    def generate_from_audio(self, audio_path: str) -> None:
        """从音频文件识别字幕"""
        self._cancelled = False
        self._thread = threading.Thread(
            target=self._run_audio, args=(audio_path,), daemon=True
        )
        self._thread.start()

    def cancel(self):
        """取消当前识别"""
        self._cancelled = True

    # ==================================================================
    #  识别实现
    # ==================================================================

    def _run_video(self, video_path: str):
        """从视频中提取音频 → 识别"""
        try:
            self.progress.emit("📝 正在从视频提取音频…")
            audio_path = self._extract_audio(video_path)
            if not audio_path:
                self.error.emit("提取音频失败")
                return
            self._recognize(audio_path)
            # 清理临时音频
            Path(audio_path).unlink(missing_ok=True)
        except Exception as e:
            logger.exception(f"[AI字幕] 视频处理异常: {e}")
            self.error.emit(str(e))

    def _run_audio(self, audio_path: str):
        """直接识别音频"""
        try:
            self._recognize(audio_path)
        except Exception as e:
            logger.exception(f"[AI字幕] 音频识别异常: {e}")
            self.error.emit(str(e))

    def _recognize(self, audio_path: str):
        """核心识别管道"""
        if self._cancelled:
            return

        # 尝试 whisper.cpp
        result = self._try_whisper(audio_path)
        if result:
            self.finished.emit(result)
            return

        # 降级为在线 Google Speech
        if self._cancelled:
            return
        result = self._try_google_speech(audio_path)
        if result:
            self.finished.emit(result)
            return

        self.error.emit("所有语音识别引擎均不可用。请安装 whisper.cpp 或检查网络。")

    # ==================================================================
    #  whisper.cpp（本地）
    # ==================================================================

    def _try_whisper(self, audio_path: str) -> Optional[list[dict]]:
        """尝试 whisper.cpp 本地识别"""
        exe = self._find_whisper()
        if not exe:
            logger.info("[AI字幕] whisper.cpp 未找到")
            return None

        model_path = self._find_whisper_model()
        if not model_path:
            logger.info("[AI字幕] whisper 模型未找到")
            return None

        self.progress.emit(f"📝 whisper.cpp ({self.whisper_model}) 识别中…")

        try:
            # whisper.cpp 命令行
            # ./whisper -m ggml-medium.bin -l zh -f audio.wav -oj
            result = subprocess.run(
                [exe, "-m", model_path, "-l", self.language,
                 "-f", audio_path, "-oj", "-of", audio_path + ".whisper"],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0 and not self._cancelled:
                logger.warning(f"[AI字幕] whisper 退出码 {result.returncode}: {result.stderr}")
                # 尝试读取已有的输出文件
        except subprocess.TimeoutExpired:
            logger.warning("[AI字幕] whisper 超时")
            return None
        except Exception as e:
            logger.warning(f"[AI字幕] whisper 执行失败: {e}")
            return None

        # 读取 JSON 输出
        json_path = audio_path + ".whisper.json"
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            Path(json_path).unlink(missing_ok=True)
            # 清理其他输出文件
            for ext in [".txt", ".srt", ".vtt"]:
                Path(audio_path + ".whisper" + ext).unlink(missing_ok=True)

            return self._whisper_to_clips(data)
        except FileNotFoundError:
            logger.warning("[AI字幕] whisper 输出 JSON 未生成")
            return None

    def _whisper_to_clips(self, data: dict) -> list[dict]:
        """whisper JSON → SubtitleClip 字典列表"""
        clips = []
        segments = data.get("segments", data.get("transcription", []))
        if not segments:
            return clips

        for seg in segments:
            clips.append({
                "text": seg.get("text", "").strip(),
                "start_time": seg.get("start", 0.0),
                "end_time": seg.get("end", 0.0),
                "font": "Microsoft YaHei",
                "font_size": 28,
                "color": "#FFFFFF",
                "position": "bottom",
                "has_outline": True,
            })
        return clips

    def _find_whisper(self) -> Optional[str]:
        """查找 whisper.cpp 可执行文件"""
        if self.whisper_path and Path(self.whisper_path).exists():
            return self.whisper_path

        # 常见路径
        candidates = [
            "whisper",
            "whisper.cpp",
            "./whisper",
            str(Path.home() / "whisper.cpp" / "whisper"),
            str(Path.home() / "whisper.cpp" / "build" / "bin" / "whisper-cli"),
        ]
        import platform
        if platform.system() == "Windows":
            candidates = [c + ".exe" for c in candidates] + candidates

        for c in candidates:
            try:
                r = subprocess.run([c, "--help"], capture_output=True, timeout=5)
                if r.returncode == 0 or "usage" in r.stderr.lower():
                    return c
            except Exception:
                continue
        return None

    def _find_whisper_model(self) -> Optional[str]:
        """查找 whisper 模型文件"""
        model_file = f"ggml-{self.whisper_model}.bin"
        candidates = [
            f"models/{model_file}",
            str(Path.home() / "whisper.cpp" / "models" / model_file),
            str(Path("models") / model_file),
        ]
        for c in candidates:
            if Path(c).exists():
                return c
        return None

    # ==================================================================
    #  Google Speech Recognition（在线降级）
    # ==================================================================

    def _try_google_speech(self, audio_path: str) -> Optional[list[dict]]:
        """使用 Google Speech Recognition 在线识别"""
        try:
            import speech_recognition as sr
        except ImportError:
            logger.info("[AI字幕] speech_recognition 未安装")
            return None

        self.progress.emit("📝 Google Speech 在线识别中…")

        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)

            text = recognizer.recognize_google(audio, language="zh-CN")
            if not text:
                return []

            # Google 只返回完整文本，无时间轴 → 生成单条字幕
            # 估算时长
            import wave
            try:
                with wave.open(audio_path) as wf:
                    total_dur = wf.getnframes() / wf.getframerate()
            except Exception:
                total_dur = 5.0

            return [{
                "text": text.strip(),
                "start_time": 0.0,
                "end_time": total_dur,
                "font": "Microsoft YaHei",
                "font_size": 28,
                "color": "#FFFFFF",
                "position": "bottom",
                "has_outline": True,
            }]
        except Exception as e:
            logger.warning(f"[AI字幕] Google Speech 失败: {e}")
            return None

    # ==================================================================
    #  音频提取
    # ==================================================================

    def _extract_audio(self, video_path: str) -> Optional[str]:
        """用 FFmpeg 从视频提取 WAV 音频"""
        fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="sub_extract_")
        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", video_path,
                 "-vn", "-acodec", "pcm_s16le",
                 "-ar", "16000", "-ac", "1", out_path],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return out_path
            logger.warning(f"[AI字幕] FFmpeg 提取音频失败: {result.stderr}")
        except Exception as e:
            logger.warning(f"[AI字幕] FFmpeg 异常: {e}")
        return None

    # ==================================================================
    #  SRT 解析（备用）
    # ==================================================================

    @staticmethod
    def parse_srt(srt_path: str) -> list[dict]:
        """解析 SRT 字幕文件 → SubtitleClip 字典列表"""
        clips = []
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return clips

        # SRT 格式:
        # 1
        # 00:00:01,000 --> 00:00:04,000
        # 字幕文本
        pattern = r'(\d+)\n(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\n(.+?)(?=\n\n|\n*\Z)'
        for m in re.finditer(pattern, content, re.DOTALL):
            sh, sm, ss, sms = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
            eh, em, es, ems = int(m.group(6)), int(m.group(7)), int(m.group(8)), int(m.group(9))
            text = m.group(10).replace("\n", " ").strip()

            clips.append({
                "text": text,
                "start_time": sh * 3600 + sm * 60 + ss + sms / 1000.0,
                "end_time": eh * 3600 + em * 60 + es + ems / 1000.0,
                "font": "Microsoft YaHei",
                "font_size": 28,
                "color": "#FFFFFF",
                "position": "bottom",
                "has_outline": True,
            })
        return clips

    @staticmethod
    def import_srt(srt_path: str, offset: float = 0.0) -> list[dict]:
        """导入外部 SRT 并应用时间偏移"""
        clips = AISubtitleEngine.parse_srt(srt_path)
        for c in clips:
            c["start_time"] += offset
            c["end_time"] += offset
        return clips
