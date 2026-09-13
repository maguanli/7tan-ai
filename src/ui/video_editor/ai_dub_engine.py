"""
AI 配音引擎 — TTS 文字转语音

Phase 5: edge-tts (在线) + 本地 pyttsx3 降级
输出 WAV/MP3 → 自动添加到素材库 + 音频轨

架构：
  文字 → TTS引擎 → 音频文件 → media_bin.add → timeline 音频轨
"""

from __future__ import annotations

import asyncio
import tempfile
import threading
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal
from loguru import logger


# ======================================================================
#  配音结果
# ======================================================================

class DubResult:
    """一次配音的结果"""
    def __init__(self, text: str, audio_path: str,
                 duration: float, engine: str):
        self.text = text
        self.audio_path = audio_path
        self.duration = duration
        self.engine = engine


# ======================================================================
#  配音引擎
# ======================================================================

class AIDubEngine(QObject):
    """AI 配音引擎

    使用方式:
        engine = AIDubEngine()
        engine.progress.connect(on_progress)
        engine.finished.connect(on_finished)
        engine.speak("欢迎收看本期视频")
    """

    progress = pyqtSignal(str)      # 进度消息
    finished = pyqtSignal(object)   # DubResult
    error = pyqtSignal(str)         # 错误消息

    def __init__(self):
        super().__init__()
        self._thread: Optional[threading.Thread] = None
        self._cancelled = False

        # 语音配置
        self.voice: str = "zh-CN-XiaoxiaoNeural"  # edge-tts 默认女声
        self.speed: float = 1.0                    # 语速倍率
        self.pitch: float = 0.0                    # 音调偏移 (-20~20 Hz)
        self.output_dir: str = ""                  # 输出目录

    # ==================================================================
    #  公开接口
    # ==================================================================

    def speak(self, text: str, output_path: str = "") -> None:
        """异步合成语音"""
        self._cancelled = False
        self.progress.emit("🎙️ 正在合成语音…")
        self._thread = threading.Thread(
            target=self._run_async, args=(text, output_path), daemon=True
        )
        self._thread.start()

    def speak_sync(self, text: str, output_path: str = "") -> Optional[DubResult]:
        """同步合成（阻塞），返回 DubResult 或 None"""
        return self._synthesize(text, output_path)

    def cancel(self):
        """取消当前合成"""
        self._cancelled = True

    def set_voice(self, voice: str):
        """切换语音角色"""
        self.voice = voice

    # ==================================================================
    #  合成实现
    # ==================================================================

    def _run_async(self, text: str, output_path: str):
        """在线程中运行 asyncio"""
        try:
            result = asyncio.run(self._try_edge_tts(text, output_path))
            if result:
                self.finished.emit(result)
            elif not self._cancelled:
                # edge-tts 失败 → 降级 pyttsx3
                result = self._try_pyttsx3(text, output_path)
                if result:
                    self.finished.emit(result)
                else:
                    self.error.emit("所有TTS引擎均不可用")
        except Exception as e:
            logger.exception(f"[AI配音] 异常: {e}")
            if not self._cancelled:
                self.error.emit(str(e))

    def _synthesize(self, text: str, output_path: str = "") -> Optional[DubResult]:
        """同步合成"""
        try:
            result = asyncio.run(self._try_edge_tts(text, output_path))
            if result:
                return result
        except Exception:
            pass
        return self._try_pyttsx3(text, output_path)

    async def _try_edge_tts(self, text: str,
                            output_path: str = "") -> Optional[DubResult]:
        """使用 edge-tts 合成（在线，高质量）"""
        try:
            import edge_tts
        except ImportError:
            logger.info("[AI配音] edge-tts 未安装，跳过")
            return None

        if self._cancelled:
            return None

        self.progress.emit("🎙️ edge-tts 合成中…")

        # 输出路径
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".mp3", prefix="dub_")
            output_path = output_path.replace("\\", "/")

        # 合成
        communicate = edge_tts.Communicate(
            text, self.voice,
            rate=f"{self.speed:+d}%",
            pitch=f"{self.pitch:+d}Hz",
        )
        await communicate.save(output_path)

        if self._cancelled:
            Path(output_path).unlink(missing_ok=True)
            return None

        # 估算时长（粗略：中文 ~4字/秒，英文 ~12字母/秒）
        duration = self._estimate_duration(text)
        logger.info(f"[AI配音] 合成完成: {output_path} ({duration:.1f}s)")

        return DubResult(
            text=text, audio_path=output_path,
            duration=duration, engine="edge-tts",
        )

    def _try_pyttsx3(self, text: str,
                      output_path: str = "") -> Optional[DubResult]:
        """使用 pyttsx3 合成（离线，低质量）"""
        try:
            import pyttsx3
        except ImportError:
            logger.info("[AI配音] pyttsx3 未安装")
            return None

        if self._cancelled:
            return None

        self.progress.emit("🎙️ pyttsx3 离线合成中…")

        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="dub_")

        engine = pyttsx3.init()
        engine.setProperty("rate", int(200 * self.speed))
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        engine.stop()

        duration = self._estimate_duration(text)
        logger.info(f"[AI配音] pyttsx3 完成: {output_path} ({duration:.1f}s)")

        return DubResult(
            text=text, audio_path=output_path,
            duration=duration, engine="pyttsx3",
        )

    # ==================================================================
    #  工具
    # ==================================================================

    @staticmethod
    def _estimate_duration(text: str) -> float:
        """粗略估算语音时长"""
        # 中文约 4 字/秒，英文约 12 字符/秒
        import re
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
        other = len(text) - chinese
        return max(chinese / 4.0 + other / 12.0, 1.0)

    @staticmethod
    def available_voices() -> list[dict]:
        """列出可用语音（edge-tts 需要在线）"""
        return [
            {"id": "zh-CN-XiaoxiaoNeural",  "name": "晓晓 (女)",   "style": "温柔"},
            {"id": "zh-CN-YunxiNeural",     "name": "云希 (男)",   "style": "沉稳"},
            {"id": "zh-CN-XiaoyiNeural",    "name": "晓伊 (女)",   "style": "活泼"},
            {"id": "zh-CN-YunjianNeural",   "name": "云健 (男)",   "style": "运动"},
            {"id": "zh-CN-YunyangNeural",   "name": "云扬 (男)",   "style": "新闻"},
            {"id": "zh-CN-YunfengNeural",   "name": "云枫 (男)",   "style": "大气"},
            {"id": "zh-CN-XiaohanNeural",   "name": "晓涵 (女)",   "style": "知性"},
        ]
