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

# === 女声配置 (Piper) — 多候选路径（E 盘本地优先 → G 盘回退，防盘符抽风） ===
def _first_existing(*paths):
    for p in paths:
        try:
            if Path(p).exists():
                return Path(p)
        except OSError:
            continue
    return Path(paths[0])

VOICE_ONNX = _first_existing(
    r"E:\7tan_voice\piper\voices\zh_CN-huayan-medium.onnx",
    r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx",
)
VOICE_JSON = _first_existing(
    r"E:\7tan_voice\piper\voices\zh_CN-huayan-medium.onnx.json",
    r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx.json",
)
OUTPUT_DIR = Path(r"E:\7tan_voice\piper\output")
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
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

# === Edge TTS 熔断器 ===
_edge_tts_circuit_open = False  # True=熔断，直接跳过 edge-tts
_edge_tts_failure_count = 0
_edge_tts_circuit_reset_time = 0  # 下次可重试的时间戳
CIRCUIT_FAILURE_THRESHOLD = 3  # 连续失败 3 次后熔断
CIRCUIT_RESET_SECONDS = 120  # 2 分钟后自动尝试恢复


def _update_circuit_breaker(success: bool):
    """更新 Edge TTS 熔断器状态"""
    global _edge_tts_circuit_open, _edge_tts_failure_count, _edge_tts_circuit_reset_time
    if success:
        _edge_tts_circuit_open = False
        _edge_tts_failure_count = 0
        _edge_tts_circuit_reset_time = 0
    else:
        _edge_tts_failure_count += 1
        if _edge_tts_failure_count >= CIRCUIT_FAILURE_THRESHOLD:
            _edge_tts_circuit_open = True
            _edge_tts_circuit_reset_time = time.time() + CIRCUIT_RESET_SECONDS
            logger.warning(
                f"[TTS] Edge TTS 熔断！连续失败 {_edge_tts_failure_count} 次，"
                f"{CIRCUIT_RESET_SECONDS}s 内自动回退 Piper"
            )


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
      5. 熔断器：连续失败自动跳过，避免反复超时
    """
    global _edge_tts_circuit_open

    # === 熔断检查 ===
    if _edge_tts_circuit_open:
        if time.time() < _edge_tts_circuit_reset_time:
            remaining = int(_edge_tts_circuit_reset_time - time.time())
            return {
                "status": "error",
                "message": f"Edge TTS 已熔断（{remaining}s 后自动恢复），请稍后再试",
                "circuit_open": True,
            }
        else:
            # 冷却时间到，尝试恢复
            _edge_tts_circuit_open = False
            _edge_tts_failure_count = 0
            logger.info("[TTS] Edge TTS 熔断冷却时间到，尝试恢复")

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
                        _update_circuit_breaker(False)
                        return {
                            "status": "error",
                            "message": (
                                f"Edge TTS 失败(已重试{EDGE_MAX_RETRIES}次): "
                                f"{last_error}"
                            ),
                        }

            # === MP3 → WAV（用于 winsound 播放） ===
            try:
                _FFMPEG = _first_existing(
                    r"E:\7tan_voice\ffmpeg\ffmpeg.exe",
                    r"G:\ffmpeg\bin\ffmpeg.exe",
                )
                subprocess.run([
                    str(_FFMPEG), "-y", "-i", mp3_path,
                    "-af", "volume=2.0", "-acodec", "pcm_s16le", "-ar", "22050",
                    wav_path
                ], capture_output=True, timeout=15, check=True)
                os.remove(mp3_path)
            except FileNotFoundError:
                # ffmpeg 二进制不存在
                logger.warning("[TTS] ffmpeg 未找到，无法转换 MP3→WAV")
                if play:
                    os.startfile(mp3_path) if os.name == 'nt' else None
                    _update_circuit_breaker(True)
                    return {
                        "status": "ok",
                        "wav_path": mp3_path,
                        "size_kb": round(os.path.getsize(mp3_path) / 1024, 1),
                        "voice": "yunxi",
                        "engine": "Edge TTS",
                    }
                else:
                    return {
                        "status": "error",
                        "message": "ffmpeg 未找到，无法将 MP3 转为 WAV（winsound 仅支持 WAV）",
                    }
            except Exception as e:
                # ffmpeg 转换失败
                logger.warning(f"[TTS] ffmpeg 转换失败: {e}")
                if play:
                    os.startfile(mp3_path) if os.name == 'nt' else None
                    _update_circuit_breaker(True)
                    return {
                        "status": "ok",
                        "wav_path": mp3_path,
                        "size_kb": round(os.path.getsize(mp3_path) / 1024, 1),
                        "voice": "yunxi",
                        "engine": "Edge TTS",
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"ffmpeg 转换失败: {e}",
                    }

            size_kb = round(os.path.getsize(wav_path) / 1024, 1)
            if play:
                threading.Thread(
                    target=_play_wav, args=(wav_path,), daemon=True
                ).start()

            if attempt > 1:
                logger.info(f"[TTS] Edge TTS 第{attempt}次重试成功")
            _update_circuit_breaker(True)
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
            _update_circuit_breaker(False)
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
            _update_circuit_breaker(False)
            return {
                "status": "error",
                "message": (
                    f"Edge TTS 失败(已重试{EDGE_MAX_RETRIES}次): {last_error}"
                ),
            }

    _update_circuit_breaker(False)
    return {"status": "error", "message": f"Edge TTS 失败: {last_error}"}


# ============================================================
# Piper TTS（女声，本地）
# ============================================================

def _speak_piper(text: str, play: bool) -> dict:
    """Piper 女声合成 → WAV → 播放"""
    voice = _get_voice()
    ts = int(time.time() * 1000)
    wav_path = str(OUTPUT_DIR / f"tts_{ts}.wav")

    # 使用 synthesize_wav 直接写入 WAV（新版 Piper API）
    with wave.open(wav_path, "wb") as wf:
        voice.synthesize_wav(text, wf)

    size_kb = round(os.path.getsize(wav_path) / 1024, 1)
    if play:
        threading.Thread(
            target=_play_wav, args=(wav_path,), daemon=True
        ).start()

    return {
        "status": "ok",
        "wav_path": wav_path,
        "size_kb": size_kb,
        "voice": "huayan",
        "engine": "Piper TTS",
    }


# ============================================================
# 统一接口
# ============================================================

def tts_speak(text: str, play: bool = True, strip_code: bool = True) -> dict:
    """
    朗读文本（根据当前性别自动选择引擎）。

    - 女声：Piper 本地合成 → 失败自动回退 Edge TTS
    - 男声：Edge TTS 在线合成 → 失败自动回退 Piper（含熔断保护）

    Args:
        text: 要朗读的文本
        play: 是否自动播放（False=仅合成不播放，调用方自行 winsound）
        strip_code: 是否移除代码块后再朗读

    Returns:
        {"status": "ok", "wav_path": "...", "fallback": True/False, ...}
    """
    if not text:
        return {"status": "error", "message": "文本为空"}

    if strip_code:
        text = _strip_code_blocks(text)

    if not text.strip():
        return {"status": "ok", "message": "移除代码块后无可朗读文本", "skipped": True}

    if _voice_gender == "male":
        # 男声：Edge TTS 主引擎，失败自动回退 Piper
        result = _speak_edge_tts(text, play)
        if result.get("status") == "error":
            logger.warning(
                f"[TTS] Edge TTS 失败，自动回退 Piper 女声: {result.get('message')}"
            )
            try:
                fallback = _speak_piper(text, play)
                fallback["fallback"] = True
                fallback["fallback_from"] = "Edge TTS → Piper"
                fallback["fallback_reason"] = result.get("message", "未知错误")
                return fallback
            except Exception as e2:
                logger.error(f"[TTS] Piper 回退也失败: {e2}")
                return result  # 返回原始错误
        return result
    else:
        # 女声：Piper 主引擎，失败自动回退 Edge TTS
        try:
            return _speak_piper(text, play)
        except Exception as e:
            logger.warning(f"[TTS] Piper 女声失败，自动回退到 Edge TTS 男声: {e}")
            return _speak_edge_tts(text, play)


def tts_status() -> dict:
    """获取 TTS 状态信息（含熔断器状态）"""
    voice_available = True
    sample_rate = None
    if _voice_gender == "female":
        try:
            voice = _get_voice()
            sample_rate = voice.config.sample_rate
        except Exception:
            voice_available = False
    else:
        voice_available = not _edge_tts_circuit_open

    result = {
        "engine": "Piper TTS" if _voice_gender == "female" else "Edge TTS",
        "gender": _voice_gender,
        "voice": "huayan (花颜)" if _voice_gender == "female" else "yunxi (云希)",
        "voice_available": voice_available,
        "sample_rate": sample_rate,
        "output_dir": str(OUTPUT_DIR),
        "playback": "winsound (async thread)",
    }

    # 熔断器状态
    if _voice_gender == "male":
        result["circuit_breaker"] = {
            "open": _edge_tts_circuit_open,
            "failure_count": _edge_tts_failure_count,
            "reset_in_seconds": (
                max(0, int(_edge_tts_circuit_reset_time - time.time()))
                if _edge_tts_circuit_open else 0
            ),
        }

    return result
