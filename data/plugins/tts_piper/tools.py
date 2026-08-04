# -*- coding: utf-8 -*-
"""
7Tan TTS 语音合成插件
女声: Piper huayan (花颜) — 纯本地 CPU 推理 | 全离线
男声: Edge TTS yunxi (云希) — 在线免费 | 自然男声
"""
import os
import time
import wave
import queue
import uuid
import threading
import re
import subprocess
import asyncio as _asyncio
import concurrent.futures
from pathlib import Path
from loguru import logger
import logging

# 🛡️ 防顶层 data 劫持：某些插件（如 iching）曾把含 data.py 的目录塞进 sys.path，
# 导致顶层模块名 `data` 被非包模块占用，`from data.plugins...` 全部报
# "No module named 'data.plugins'; 'data' is not a package"（语音功能失效）。
# 这里检测并清除被劫持的 data，让 Python 重新从 data 包导入。
import sys as _sys
if "data" in _sys.modules and not hasattr(_sys.modules["data"], "__path__"):
    _sys.modules.pop("data", None)

# 静音 piper 库的巨型 DEBUG 日志（synthesize 时打印 text + 完整 phonemes 音素表，
# 单条可达数千字符，会刷屏控制台/文件日志）。此处在插件加载源头兜底，
# 即使 logger.setup 未调用也生效。
logging.getLogger("piper").setLevel(logging.WARNING)

# === 女声配置 (Piper) — 多候选路径（E 盘本地优先 → G 盘回退，防盘符抽风） ===
def _first_existing(*paths):
    for p in paths:
        try:
            if Path(p).exists():
                return Path(p)
        except OSError:
            continue
    return Path(paths[0])

_PKG_DIR = Path(__file__).resolve().parent
VOICE_ONNX = _first_existing(
    str(_PKG_DIR / "models" / "zh_CN-huayan-medium.onnx"),
    r"E:\7tan_voice\piper\voices\zh_CN-huayan-medium.onnx",
    r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx",
)
VOICE_JSON = _first_existing(
    str(_PKG_DIR / "models" / "zh_CN-huayan-medium.onnx.json"),
    r"E:\7tan_voice\piper\voices\zh_CN-huayan-medium.onnx.json",
    r"G:\piper\piper\voices\zh_CN-huayan-medium.onnx.json",
)


def _pick_output_dir():
    """输出目录：E 盘优先 → G 盘回退 → 用户目录兜底（打包后无 E/G 盘也能用）"""
    for cand in (Path(r"E:\7tan_voice\piper\output"), Path(r"G:\piper\output")):
        try:
            cand.mkdir(parents=True, exist_ok=True)
            return cand
        except OSError:
            continue
    fallback = Path.home() / "7tan_voice" / "piper" / "output"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


OUTPUT_DIR = _pick_output_dir()

# === 男声配置 (Edge TTS) ===
MALE_VOICE = "zh-CN-YunxiNeural"  # 云希 — 年轻自然男声
MALE_VOLUME = "+80%"  # 男声默认偏小，加 80% 对齐女声音量

_voice = None
_voice_lock = threading.Lock()

# === 全局播放队列（单线程串行播放，杜绝互相打断/线程堆积） ===
_play_queue = queue.Queue()
_play_pending = set()  # 队列中待播 WAV 路径（去重，杜绝同一文件播放两次）
_player_started = False
_player_lock = threading.Lock()

# === 播放忙碌状态（供控制台/其他通道判断"正在朗读"避免重复出声） ===
_tts_busy = False
_tts_busy_lock = threading.Lock()


def _set_tts_busy(v: bool) -> None:
    global _tts_busy
    with _tts_busy_lock:
        _tts_busy = v


def tts_is_busy() -> bool:
    """是否正在播放或队列中有待播音频（True=正在出声/排队中，其他通道应跳过）"""
    with _tts_busy_lock:
        if _tts_busy:
            return True
    # 🆕 播放队列中还有待播音频 → 也视为忙碌：防控制台/聊天页重复排队出声
    with _player_lock:
        return _play_queue.qsize() > 0 or len(_play_pending) > 0


def _player_worker():
    """播放线程：串行播放队列中的 WAV，播完再取下一条（不再互相打断）"""
    while True:
        wav_path = _play_queue.get()
        if wav_path is None:  # 停止信号
            break
        try:
            if not os.path.exists(wav_path):
                logger.warning(f"[TTS] 播放失败：文件不存在 {wav_path}")
            elif os.path.getsize(wav_path) < 1024:
                # 0 字节/损坏文件直接跳过（防 winsound 卡死或爆音）
                logger.warning(f"[TTS] 播放跳过：文件过小(疑似损坏) {os.path.basename(wav_path)}")
            else:
                logger.info(f"[TTS] ▶ 播放: {os.path.basename(wav_path)} ({os.path.getsize(wav_path) // 1024}KB)")
                _set_tts_busy(True)
                import winsound
                # 同步播放：阻塞直到播完（SND_FILENAME 默认同步）
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                logger.info("[TTS] ⏹ 播放完成")
                _set_tts_busy(False)
        except Exception as e:
            logger.warning(f"[TTS] 播放失败（音频设备不可用？）: {wav_path}: {e}")
            # 兜底：winsound 失败时用系统默认播放器，至少能出声
            try:
                if os.name == 'nt' and os.path.exists(wav_path):
                    os.startfile(wav_path)
            except Exception:
                pass
        finally:
            # 从待播集合移除（允许同路径文件后续重新入队）
            with _player_lock:
                _play_pending.discard(wav_path)
            # 播完清理临时文件，防止 OUTPUT_DIR 膨胀
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except OSError:
                pass

def _ensure_player():
    """确保播放线程已启动（单例）"""
    global _player_started
    if not _player_started:
        with _player_lock:
            if not _player_started:
                threading.Thread(
                    target=_player_worker, daemon=True, name="tts-player"
                ).start()
                _player_started = True

def _enqueue_play(wav_path: str) -> None:
    """WAV 入队播放（异步返回，不阻塞调用方，不打断正在播放的声音）

    去重：同一 WAV 路径已在队列中则忽略，杜绝"最后一句播放两次"。
    """
    with _player_lock:
        if wav_path in _play_pending:
            logger.debug(f"[TTS] 忽略重复入队: {os.path.basename(wav_path)}")
            return
        _play_pending.add(wav_path)
    _set_tts_busy(True)
    _ensure_player()
    _play_queue.put(wav_path)

def tts_stop() -> dict:
    """停止播放：清空队列并停止当前正在播放的声音"""
    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass
    try:
        while not _play_queue.empty():
            try:
                _play_queue.get_nowait()
            except queue.Empty:
                break
    except Exception:
        pass
    with _player_lock:
        _play_pending.clear()
    return {"status": "ok", "message": "播放已停止"}

# === 性别切换 ===
_voice_gender: str = "female"  # "female" | "male"

# === Edge TTS 并发锁 ===
_edge_lock = threading.Lock()
EDGE_MAX_RETRIES = 1  # 失败快速回退，避免用户等 30-60 秒才听到声音
EDGE_RETRY_DELAY = 1  # 秒

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
    """播放 WAV 文件（入队串行播放，不打断其他声音）"""
    _enqueue_play(wav_path)


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
    global _voice_gender, _dedup_spoken, _dedup_ts, _dedup_pending
    gender = gender.lower().strip()
    if gender not in ("female", "male"):
        return {"status": "error", "message": f"无效性别: {gender}，可选 female / male"}

    _voice_gender = gender
    # 🔄 切换声音时清空去重状态：防止旧声音的"已朗读"登记让新声音 5 分钟静音
    with _dedup_lock:
        _dedup_spoken = ""
        _dedup_ts = 0.0
        _dedup_pending = ""
    logger.info("[TTS] 切换声音: %s，已清空去重状态", gender)
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

def _run_edge_tts_api(text: str, voice: str, output_path: str, timeout: int = 6) -> None:
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
        # 统一在新线程中运行并强制超时（无论当前线程是否已有事件循环，
        # 避免网络卡死时无限等待 → 朗读延迟高达 10+ 秒）
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_asyncio.run, _synthesize())
            future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
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
    uid = uuid.uuid4().hex[:8]
    mp3_path = str(OUTPUT_DIR / f"tts_{ts}_{uid}.mp3")
    wav_path = str(OUTPUT_DIR / f"tts_{ts}_{uid}.wav")

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
                        cmd, capture_output=True, text=True, timeout=6
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
                ], capture_output=True, timeout=10, check=True)
                os.remove(mp3_path)
            except FileNotFoundError:
                # ffmpeg 二进制不存在
                logger.warning("[TTS] ffmpeg 未找到，无法转换 MP3→WAV")
                if play:
                    os.startfile(mp3_path) if os.name == 'nt' else None
                    _notify_tts_start(text)
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
                    _notify_tts_start(text)
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
                _play_wav(wav_path)
                _notify_tts_start(text)

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
    uid = uuid.uuid4().hex[:8]
    wav_path = str(OUTPUT_DIR / f"tts_{ts}_{uid}.wav")

    # 使用 synthesize_wav 直接写入 WAV（新版 Piper API）
    with wave.open(wav_path, "wb") as wf:
        voice.synthesize_wav(text, wf)

    size_kb = round(os.path.getsize(wav_path) / 1024, 1)
    if play:
        _play_wav(wav_path)
        _notify_tts_start(text)

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

# === 朗读开始通知回调（供 UI 显示"正在语音说话"提示） ===
_tts_start_callbacks = []
_tts_start_lock = threading.Lock()


def register_tts_start_callback(callback) -> None:
    """注册朗读开始回调（幂等）。实际出声（播放队列入队）时调用 callback(text)。"""
    if not callable(callback):
        return
    with _tts_start_lock:
        if callback not in _tts_start_callbacks:
            _tts_start_callbacks.append(callback)


def _notify_tts_start(text: str) -> None:
    """通知所有已注册回调：一段文本已开始朗读（已入播放队列）。"""
    if not text:
        return
    with _tts_start_lock:
        cbs = list(_tts_start_callbacks)
    for cb in cbs:
        try:
            cb(text)
        except Exception as e:
            logger.warning(f"[TTS] 朗读开始回调异常: {e}")


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


# === 全局防重朗读（多通道共享：聊天页/全局桥/Agent 回调都走这里，同一全文 5 分钟内只朗读一次） ===
_dedup_spoken = ""
_dedup_ts = 0.0
_dedup_pending = ""  # 正在合成中的文本（抢占标记，防并发重复合成）
_dedup_lock = threading.Lock()
DEDUP_WINDOW = 300  # 秒（5 分钟）


def _dedup_clean(text: str) -> str:
    """统一去重键：去除代码块后的纯净文本（与朗读内容一致）"""
    return _strip_code_blocks((text or "").strip())


def _acquire_synth_slot(clean: str) -> bool:
    """抢占全局合成位（互斥：同一时刻只允许一个合成任务）。

    - 任何文本正在合成（_dedup_pending 非空）→ 直接跳过（防聊天页+控制台
      并行合成同一轮回复导致重复朗读，防重读优先）
    - 该文本已被朗读（5 分钟窗口）→ False
    - 成功抢占 → True（调用方负责在完成/异常后释放）
    """
    global _dedup_spoken, _dedup_ts, _dedup_pending
    with _dedup_lock:
        if clean == _dedup_spoken and time.time() - _dedup_ts < DEDUP_WINDOW:
            logger.info("[TTS] 该文本 5 分钟内已朗读，跳过（防重复）")
            return False
        if _dedup_pending:
            logger.info("[TTS] 全局互斥：已有文本正在合成中，跳过（防并行合成重复朗读）")
            return False
        _dedup_pending = clean
        return True


def tts_speak_dedup(text: str) -> dict:
    """带全局去重的朗读：同一全文 5 分钟内只朗读一次。

    供聊天页 _speak_response 与全局语音桥共用，保证多通道（agent 回调 /
    _on_response / 工作台任务）同时触发时也只会出声一次。

    两阶段防静音设计：
      1. _dedup_pending 原子抢占：并发多通道只有第一个进入合成，其余跳过（防 3 遍）
      2. 合成成功才转 _dedup_spoken（防 5 分钟静音）；任何异常/失败都释放占位，
         允许后续通道重试（防"登记残留 → 全通道静音"）
    """
    global _dedup_spoken, _dedup_ts, _dedup_pending
    clean = _dedup_clean(text)
    if not clean:
        return {"status": "ok", "message": "空文本", "skipped": True}
    with _dedup_lock:
        now = time.time()
        if clean == _dedup_spoken and now - _dedup_ts < DEDUP_WINDOW:
            logger.info("[TTS] 全局去重：同一全文 5 分钟内已朗读，跳过")
            return {"status": "ok", "skipped": True, "message": "去重跳过"}
        if clean == _dedup_pending:
            logger.info("[TTS] 全局去重：同一全文正在朗读中，跳过")
            return {"status": "ok", "skipped": True, "message": "合成中跳过"}
    # ⚡ 原子抢占 + 全局合成互斥：任何文本在合成中 → 最多等待 4 秒（防聊天页+控制台并行合成导致重复朗读）
    if not _acquire_synth_slot(clean):
        return {"status": "ok", "skipped": True, "message": "合成互斥跳过"}
    try:
        # 合成 + 播放（同步合成，异步队列播放）
        result = tts_speak(clean, play=True, strip_code=True)
    except Exception as e:
        # 🛡️ 任何异常都释放占位，绝不残留登记（防 5 分钟静音）
        with _dedup_lock:
            if _dedup_pending == clean:
                _dedup_pending = ""
        logger.error("[TTS] 朗读异常（已释放去重占位）: %s: %s", type(e).__name__, e)
        return {"status": "error", "message": f"朗读异常: {type(e).__name__}: {e}"}
    with _dedup_lock:
        if _dedup_pending == clean:
            _dedup_pending = ""
    if result.get("status") == "ok" and not result.get("skipped"):
        # ✅ 合成成功（音频已入播放队列）→ 转正式"已朗读"登记（5 分钟防重）
        with _dedup_lock:
            _dedup_spoken = clean
            _dedup_ts = time.time()
        logger.info("[TTS] 朗读成功，已登记去重（5 分钟）")
    else:
        # ❌ 未成功：不登记，允许后续重试（防失败锁死）
        logger.warning("[TTS] 朗读未成功，不登记去重: %s", result.get("message", "?"))
    return result


def tts_clear_spoken(text: str) -> dict:
    """清除某文本的已朗读登记（失败回滚用，让其他通道可重试）"""
    global _dedup_spoken, _dedup_ts
    clean = _dedup_clean(text)
    if not clean:
        return {"status": "ok", "message": "空文本"}
    with _dedup_lock:
        if _dedup_spoken == clean:
            _dedup_spoken = ""
            _dedup_ts = 0.0
            logger.info("[TTS] 已清除朗读登记（失败回滚）")
    return {"status": "ok"}


def tts_mark_spoken(text: str) -> dict:
    """标记某段文本为'已朗读'（只注册全局去重键，不实际朗读）。

    供流式朗读场景使用：流式已逐句朗读全文后调用，
    防止控制台 Agent 朗读触发 / 全局语音桥与流式朗读重复。
    """
    global _dedup_spoken, _dedup_ts
    clean = _dedup_clean(text)
    if not clean:
        return {"status": "ok", "message": "空文本", "skipped": True}
    with _dedup_lock:
        _dedup_spoken = clean
        _dedup_ts = time.time()
        logger.info("[TTS] 已标记为已朗读（去重注册，不实际播放）")
    return {"status": "ok", "skipped": False}


def tts_is_spoken(text: str) -> bool:
    """查询某文本是否已在全局去重窗口（5 分钟）内朗读/标记过。

    供控制台朗读等通道判断：聊天页已读的内容不再重复朗读。
    """
    clean = _dedup_clean(text)
    if not clean:
        return True  # 空文本视为已处理，避免无意义朗读
    with _dedup_lock:
        now = time.time()
        if clean == _dedup_spoken and now - _dedup_ts < DEDUP_WINDOW:
            return True
        # 🆕 合成中（pending 抢占）也视为已处理：防聊天页合成期间控制台重复朗读
        if clean == _dedup_pending:
            return True
        return False
