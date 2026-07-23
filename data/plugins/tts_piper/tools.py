# -*- coding: utf-8 -*-
"""
7Tan Piper TTS 语音合成插件
huayan (花颜) 中文女声 | 纯本地 CPU 推理 | 全离线
"""
import os
import time
import wave
import threading
import re
from pathlib import Path

# === 配置 ===
VOICE_ONNX = Path(r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx")
VOICE_JSON = Path(r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx.json")
OUTPUT_DIR = Path(r"G:\piper\output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_voice = None
_voice_lock = threading.Lock()


def _get_voice():
    """延迟加载 PiperVoice，线程安全"""
    global _voice
    if _voice is None:
        with _voice_lock:
            if _voice is None:
                from piper.voice import PiperVoice
                _voice = PiperVoice.load(str(VOICE_ONNX), str(VOICE_JSON))
    return _voice


def _play_wav(wav_path: str) -> None:
    """播放 WAV 文件（异步）"""
    import winsound
    winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)


def _strip_code_blocks(text: str) -> str:
    """移除代码块和特殊符号，只保留适合朗读的自然语言"""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'[*_~#>{}\[\]|]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def tts_speak(text: str, play: bool = True, strip_code: bool = True) -> dict:
    """
    TTS 语音合成 - huayan（花颜）中文女声。

    Args:
        text: 要朗读的文本
        play: 是否自动播放（默认 True）
        strip_code: 是否自动移除代码块（默认 True）

    Returns:
        {"status": "ok", "wav_path": "...", "size_kb": ..., "duration_sec": ...}
    """
    if not text or not text.strip():
        return {"status": "error", "message": "文本为空"}

    if strip_code:
        text = _strip_code_blocks(text)

    if not text.strip():
        return {"status": "ok", "message": "移除代码块后无可朗读文本", "skipped": True}

    try:
        voice = _get_voice()
        ts = int(time.time() * 1000)
        wav_path = str(OUTPUT_DIR / f"tts_{ts}.wav")

        with wave.open(wav_path, 'wb') as wav_file:
            voice.synthesize_wav(text, wav_file)

        size_kb = round(os.path.getsize(wav_path) / 1024, 1)
        duration_sec = round(size_kb / (voice.config.sample_rate * 2 / 1024), 2)

        if play:
            threading.Thread(target=_play_wav, args=(wav_path,), daemon=True).start()

        return {
            "status": "ok",
            "wav_path": wav_path,
            "size_kb": size_kb,
            "duration_sec": duration_sec,
            "voice": "huayan",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def tts_status() -> dict:
    """查看 TTS 状态"""
    voice_available = VOICE_ONNX.exists() and VOICE_JSON.exists()
    sample_rate = None
    if voice_available:
        try:
            voice = _get_voice()
            sample_rate = voice.config.sample_rate
        except Exception:
            pass

    return {
        "engine": "Piper TTS",
        "voice": "huayan (花颜)",
        "voice_available": voice_available,
        "sample_rate": sample_rate,
        "output_dir": str(OUTPUT_DIR),
        "playback": "winsound (async thread)",
    }
