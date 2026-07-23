# -*- coding: utf-8 -*-
"""
7Tan TTS 语音合成插件
女声: Piper huayan (花颜) — 纯本地 CPU 推理 | 全离线
男声: Edge TTS yunxi (云希) — 在线免费 | 自然男声
"""
import os
import time
import wave
import threading
import re
import subprocess
from pathlib import Path

# === 女声配置 (Piper) ===
VOICE_ONNX = Path(r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx")
VOICE_JSON = Path(r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx.json")
OUTPUT_DIR = Path(r"G:\piper\output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# === 男声配置 (Edge TTS) ===
MALE_VOICE = "zh-CN-YunxiNeural"  # 云希 — 年轻自然男声
MALE_VOLUME = "+80%"  # 男声默认偏小，加 80% 对齐女声音量

_voice = None
_voice_lock = threading.Lock()

# === 性别切换 ===
_voice_gender: str = "female"  # "female" | "male"


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


def tts_set_gender(gender: str) -> dict:
    """
    切换 TTS 声音性别。

    Args:
        gender: "female"（花颜女声 / Piper 本地）或 "male"（云希男声 / Edge TTS 在线）

    Returns:
        {"status": "ok", "gender": "...", "voice": "..."}
    """
    global _voice_gender
    gender = gender.lower().strip()
    if gender not in ("female", "male"):
        return {"status": "error", "message": f"无效性别: {gender}，可选 female / male"}

    _voice_gender = gender
    if gender == "female":
        return {"status": "ok", "gender": "female", "voice": "huayan (花颜)", "engine": "Piper (本地)"}
    else:
        return {"status": "ok", "gender": "male", "voice": "yunxi (云希)", "engine": "Edge TTS (在线)"}


def tts_get_gender() -> dict:
    """获取当前 TTS 声音性别"""
    if _voice_gender == "male":
        return {"gender": "male", "voice": "yunxi (云希)", "engine": "Edge TTS"}
    return {"gender": "female", "voice": "huayan (花颜)", "engine": "Piper TTS"}


def _speak_edge_tts(text: str, play: bool) -> dict:
    """Edge TTS 男声合成 → WAV → 播放"""
    ts = int(time.time() * 1000)
    mp3_path = str(OUTPUT_DIR / f"tts_{ts}.mp3")
    wav_path = str(OUTPUT_DIR / f"tts_{ts}.wav")

    try:
        # 使用 edge-tts CLI（最可靠方式）
        cmd = [
            "edge-tts", "--voice", MALE_VOICE,
            "--volume", MALE_VOLUME,
            "--text", text,
            "--write-media", mp3_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return {"status": "error", "message": f"Edge TTS 失败: {result.stderr[:200]}"}

        # MP3 → WAV（用于 winsound 播放）
        try:
            subprocess.run([
                r"G:\ffmpeg\bin\ffmpeg.exe", "-y", "-i", mp3_path,
                "-af", "volume=2.0", "-acodec", "pcm_s16le", "-ar", "22050",
                wav_path
            ], capture_output=True, timeout=15, check=True)
            os.remove(mp3_path)
        except Exception:
            # ffmpeg 不可用时直接用 mp3（winsound 不支持 mp3，但保留文件）
            wav_path = mp3_path
            # 尝试用 Windows Media Player 播放 mp3
            if play:
                os.startfile(mp3_path) if os.name == 'nt' else None
            return {
                "status": "ok",
                "wav_path": mp3_path,
                "size_kb": round(os.path.getsize(mp3_path) / 1024, 1),
                "voice": "yunxi",
                "engine": "Edge TTS",
            }

        size_kb = round(os.path.getsize(wav_path) / 1024, 1)
        if play:
            threading.Thread(target=_play_wav, args=(wav_path,), daemon=True).start()

        return {
            "status": "ok",
            "wav_path": wav_path,
            "size_kb": size_kb,
            "voice": "yunxi",
            "engine": "Edge TTS",
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Edge TTS 超时（30秒）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _speak_piper(text: str, play: bool) -> dict:
    """Piper 女声合成 → WAV → 播放"""
    voice = _get_voice()
    ts = int(time.time() * 1000)
    wav_path = str(OUTPUT_DIR / f"tts_{ts}.wav")

    with wave.open(wav_path, 'wb') as wav_file:
        voice.synthesize_wav(text, wav_file)

    size_kb = round(os.path.getsize(wav_path) / 1024, 1)

    if play:
        threading.Thread(target=_play_wav, args=(wav_path,), daemon=True).start()

    return {
        "status": "ok",
        "wav_path": wav_path,
        "size_kb": size_kb,
        "voice": "huayan",
        "engine": "Piper TTS",
    }


def tts_speak(text: str, play: bool = True, strip_code: bool = True) -> dict:
    """
    TTS 语音合成 — 根据当前性别设置自动选择引擎。

    Args:
        text: 要朗读的文本
        play: 是否自动播放（默认 True）
        strip_code: 是否自动移除代码块（默认 True）

    Returns:
        {"status": "ok", "wav_path": "...", "voice": "huayan"|"yunxi", ...}
    """
    if not text or not text.strip():
        return {"status": "error", "message": "文本为空"}

    if strip_code:
        text = _strip_code_blocks(text)

    if not text.strip():
        return {"status": "ok", "message": "移除代码块后无可朗读文本", "skipped": True}

    if _voice_gender == "male":
        return _speak_edge_tts(text, play)
    else:
        return _speak_piper(text, play)


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
        "engine": "Piper TTS" if _voice_gender == "female" else "Edge TTS",
        "gender": _voice_gender,
        "voice": "huayan (花颜)" if _voice_gender == "female" else "yunxi (云希)",
        "voice_available": voice_available,
        "sample_rate": sample_rate,
        "output_dir": str(OUTPUT_DIR),
        "playback": "winsound (async thread)",
    }
