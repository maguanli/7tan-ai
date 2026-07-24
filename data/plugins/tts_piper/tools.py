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
import asyncio as _asyncio
import concurrent.futures
from pathlib import Path
from loguru import logger

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

# === Edge TTS 并发锁 ===
_edge_lock = threading.Lock()
EDGE_MAX_RETRIES = 3
EDGE_RETRY_DELAY = 2  # 秒


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


# ============================================================
# Edge TTS 核心 — Python API 优先 + CLI 回退
# ============================================================

def _run_edge_tts_api(text: str, voice: str, output_path: str, timeout: int = 30) -> None:
    """
    使用 edge_tts Python API 合成语音（无子进程，更可靠）。

    Raises:
        TimeoutError: 合成超时
        Exception: 其他 edge_tts 内部错误
    """
    async def _synthesize():
        communicate = __import__('edge_tts').Communicate(text, voice)
        with open(output_path, 'wb') as f:
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    f.write(chunk['data'])
                elif chunk['type'] == 'WordBoundary':
                    pass  # 忽略词边界事件

    try:
        # 检查当前线程是否已有事件循环（如 GUI 主线程）
        try:
            _asyncio.get_running_loop()
            # 已有事件循环 → 在新线程中运行（避免嵌套事件循环）
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_asyncio.run, _synthesize())
                future.result(timeout=timeout)
        except RuntimeError:
            # 当前线程无事件循环 → 直接运行
            _asyncio.run(_synthesize())
    except _asyncio.TimeoutError:
        raise TimeoutError(f"Edge TTS API 超时（{timeout}秒）")


def _speak_edge_tts(text: str, play: bool) -> dict:
    """
    Edge TTS 男声合成 → WAV → 播放。

    策略:
      1. 优先使用 Python API（edge_tts.Communicate）— 无子进程，更稳定
      2. API 失败则回退到 CLI（edge-tts 命令行）
      3. 失败自动重试（最多 EDGE_MAX_RETRIES 次）
      4. 并发锁防止多线程同时调用
    """
    ts = int(time.time() * 1000)
    mp3_path = str(OUTPUT_DIR / f"tts_{ts}.mp3")
    wav_path = str(OUTPUT_DIR / f"tts_{ts}.wav")

    last_error = ""
    for attempt in range(1, EDGE_MAX_RETRIES + 1):
        try:
            # 并发锁：防止两个线程同时调用 edge-tts
            with _edge_lock:
                # === 方法1: Python API（优先） ===
                api_success = False
                try:
                    _run_edge_tts_api(text, MALE_VOICE, mp3_path)
                    api_success = True
                    logger.debug(f"[TTS] Python API 合成成功 ({os.path.getsize(mp3_path)} bytes)")
                except Exception as api_err:
                    logger.info(
                        f"[TTS] Python API 失败 → 回退 CLI: "
                        f"{type(api_err).__name__}: {api_err}"
                    )

                # === 方法2: CLI 回退 ===
                if not api_success:
                    cmd = [
                        "edge-tts", "--voice", MALE_VOICE,
                        "--volume", MALE_VOLUME,
                        "--text", text,
                        "--write-media", mp3_path,
                    ]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=30
                    )
                    if result.returncode != 0:
                        last_error = (
                            result.stderr or f"返回码 {result.returncode}"
                        )[:800]
                        logger.warning(
                            f"[TTS] Edge TTS CLI 第{attempt}/{EDGE_MAX_RETRIES}"
                            f"次失败: {last_error}"
                        )
                        if attempt < EDGE_MAX_RETRIES:
                            time.sleep(EDGE_RETRY_DELAY * attempt)
                            continue
                        return {
                            "status": "error",
                            "message": (
                                f"Edge TTS 失败(已重试{EDGE_MAX_RETRIES}次): "
                                f"{last_error}"
                            ),
                        }

            # === MP3 → WAV（用于 winsound 播放） ===
            try:
                subprocess.run([
                    r"G:\ffmpeg\bin\ffmpeg.exe", "-y", "-i", mp3_path,
                    "-af", "volume=2.0", "-acodec", "pcm_s16le", "-ar", "22050",
                    wav_path
                ], capture_output=True, timeout=15, check=True)
                os.remove(mp3_path)
            except Exception:
                # ffmpeg 不可用 → 直接播放 MP3
                wav_path = mp3_path
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
                threading.Thread(
                    target=_play_wav, args=(wav_path,), daemon=True
                ).start()

            if attempt > 1:
                logger.info(f"[TTS] Edge TTS 第{attempt}次重试成功")
            return {
                "status": "ok",
                "wav_path": wav_path,
                "size_kb": size_kb,
                "voice": "yunxi",
                "engine": "Edge TTS",
            }

        except subprocess.TimeoutExpired:
            last_error = "超时（30秒）"
            logger.warning(
                f"[TTS] Edge TTS 第{attempt}/{EDGE_MAX_RETRIES}次超时"
            )
            if attempt < EDGE_MAX_RETRIES:
                time.sleep(EDGE_RETRY_DELAY * attempt)
                continue
            return {
                "status": "error",
                "message": f"Edge TTS 超时(已重试{EDGE_MAX_RETRIES}次)",
            }
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"[:500]
            logger.warning(
                f"[TTS] Edge TTS 第{attempt}/{EDGE_MAX_RETRIES}"
                f"次异常: {last_error}"
            )
            if attempt < EDGE_MAX_RETRIES:
                time.sleep(EDGE_RETRY_DELAY * attempt)
                continue
            return {
                "status": "error",
                "message": (
                    f"Edge TTS 失败(已重试{EDGE_MAX_RETRIES}次): {last_error}"
                ),
            }

    return {"status": "error", "message": f"Edge TTS 失败: {last_error}"}


# ============================================================
# Piper TTS（女声，本地）
# ============================================================

def _speak_piper(text: str, play: bool) -> dict:
    """Piper 女声合成 → WAV → 播放"""
    voice = _get_voice()
    ts = int(time.time() * 1000)
    wav_path = str(OUTPUT_DIR / f"tts_{ts}.wav")

    # 生成原始 PCM 数据
    audio_data = b""
    for chunk in voice.synthesize_stream_raw(text):
        audio_data += chunk

    # 写入 WAV
    sample_rate = voice.config.sample_rate
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)

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


# ============================================================
# 公共 API
# ============================================================

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
        try:
            return _speak_piper(text, play)
        except Exception as e:
            logger.warning(f"[TTS] Piper 女声失败，自动回退到 Edge TTS 男声: {e}")
            return _speak_edge_tts(text, play)


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
