# -*- coding: utf-8 -*-
"""
7Tan Whisper STT 语音识别插件
whisper.cpp small 模型 | 纯本地 CPU | 中文识别
"""
import subprocess
import os
import time
import threading
import wave
from pathlib import Path

def _first_existing(*paths):
    for p in paths:
        try:
            if Path(p).exists():
                return Path(p)
        except OSError:
            continue
    return Path(paths[0])

# 多候选路径（E 盘本地优先 → G 盘回退，防盘符抽风）
WHISPER_CLI = _first_existing(
    r"E:\7tan_voice\whisper\whisper-cli.exe",
    r"G:\whisper_cpp\Release\whisper-cli.exe",
)
WHISPER_Model = _first_existing(
    r"E:\7tan_voice\whisper\ggml-small.bin",
    r"G:\whisper_cpp\models\ggml-small.bin",
)
FFMPEG = _first_existing(
    r"E:\7tan_voice\ffmpeg\ffmpeg.exe",
    r"G:\ffmpeg\bin\ffmpeg.exe",
)
TEMP_DIR = Path(os.environ.get("TEMP", r"C:\Windows\Temp")) / "7tan_stt"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

_recording = False
_record_thread = None


def _record_audio(output_path: str, duration: float, sample_rate: int = 16000) -> bool:
    """录音指定秒数，保存为 WAV"""
    try:
        import sounddevice as sd
        import numpy as np

        # 单声道 16kHz 录音
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()

        # 写入 WAV
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())

        return True
    except Exception as e:
        print(f"[STT] 录音失败: {e}")
        return False


def _wav_sample_rate(path: str) -> int:
    """读取 WAV 文件采样率（失败返回 -1）"""
    try:
        with wave.open(path, 'rb') as wf:
            return wf.getframerate()
    except Exception:
        return -1


def _resample_to_16k(src_path: str) -> str:
    """
    若 WAV 采样率不是 16kHz，用 ffmpeg 重采样为 16kHz 单声道（whisper 最佳输入）。

    修复：高采样率（22050/44100 等）音频直接识别会空结果/乱码的问题。

    Returns:
        识别用路径；已是 16kHz 或重采样失败时返回原路径。
    """
    rate = _wav_sample_rate(src_path)
    if rate == 16000:
        return src_path
    if rate <= 0:
        return src_path  # 非 WAV / 读不到采样率 → 原样尝试

    if not FFMPEG.exists():
        print(f"[STT] ffmpeg 不存在，无法重采样 {rate}Hz → 16000Hz，原样识别")
        return src_path

    dst = TEMP_DIR / f"resample_{int(time.time() * 1000)}.wav"
    try:
        result = subprocess.run(
            [str(FFMPEG), "-y", "-i", src_path,
             "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
             str(dst)],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0 and dst.exists() and dst.stat().st_size > 44:
            print(f"[STT] 重采样 {rate}Hz → 16000Hz 成功")
            return str(dst)
        return src_path
    except Exception as e:
        print(f"[STT] 重采样失败: {e}")
        return src_path


def _transcribe(wav_path: str) -> str:
    """用 whisper.cpp 识别语音"""
    try:
        result = subprocess.run(
            [str(WHISPER_CLI),
             "-m", str(WHISPER_Model),
             "-l", "zh",
             "--no-timestamps",
             "-t", "4",
             str(wav_path)],
            capture_output=True,
            timeout=120,
            cwd=str(WHISPER_CLI.parent),  # 用 exe 所在目录（E 盘时 dll 同目录）
        )

        if result.returncode != 0:
            return ""

        # 从输出中提取识别结果
        raw = result.stdout.decode('utf-8', errors='replace')
        lines = raw.split('\n')

        # 过滤掉技术日志，保留识别结果
        rec_lines = []
        for line in lines:
            if line.strip() and not any(kw in line for kw in [
                'whisper_', 'read_audio', 'load_backend', 'ggml_',
                'system_info', 'whisper_init', 'llama_', 'whisper_backend',
            ]):
                rec_lines.append(line.strip())

        return ' '.join(rec_lines).strip()

    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        print(f"[STT] 识别失败: {e}")
        return ""


def stt_listen(duration: float = 5) -> dict:
    """
    录音并识别为文字。阻塞式，默认录制 5 秒。

    Args:
        duration: 录音时长（秒），建议 3-10 秒

    Returns:
        {"status": "ok", "text": "识别结果", "duration_sec": ...}
    """
    if not WHISPER_CLI.exists():
        return {"status": "error", "message": f"whisper-cli 不存在: {WHISPER_CLI}"}
    if not WHISPER_Model.exists():
        return {"status": "error", "message": f"模型不存在: {WHISPER_Model}"}

    if duration < 1:
        duration = 3
    if duration > 30:
        duration = 30

    timestamp = int(time.time() * 1000)
    wav_path = TEMP_DIR / f"rec_{timestamp}.wav"

    # 录音
    t0 = time.time()
    ok = _record_audio(str(wav_path), duration)
    if not ok:
        return {"status": "error", "message": "录音失败"}

    record_time = time.time() - t0

    # 识别
    t1 = time.time()
    text = _transcribe(str(wav_path))
    transcribe_time = time.time() - t1

    # 清理临时文件
    try:
        os.remove(str(wav_path))
    except Exception:
        pass

    return {
        "status": "ok" if text else "empty",
        "text": text,
        "record_sec": round(record_time, 2),
        "transcribe_sec": round(transcribe_time, 2),
        "total_sec": round(record_time + transcribe_time, 2),
    }


def stt_transcribe_file(wav_path: str) -> dict:
    """
    识别已有的 WAV 文件（自动重采样到 16kHz，兼容任意采样率）。

    Args:
        wav_path: WAV 文件路径（任意采样率，自动转为 16kHz 单声道）

    Returns:
        {"status": "ok", "text": "识别结果"}
    """
    if not os.path.exists(wav_path):
        return {"status": "error", "message": f"文件不存在: {wav_path}"}

    t0 = time.time()
    # P1: 自动重采样到 16kHz（whisper 最佳输入，修复高采样率识别为空/乱码）
    work_path = _resample_to_16k(wav_path)
    text = _transcribe(work_path)
    # 清理重采样临时文件
    if work_path != wav_path:
        try:
            os.remove(work_path)
        except Exception:
            pass
    elapsed = time.time() - t0

    return {
        "status": "ok" if text else "empty",
        "text": text,
        "elapsed_sec": round(elapsed, 2),
    }


def stt_status() -> dict:
    """查看 STT 状态"""
    return {
        "engine": "whisper.cpp",
        "model": "ggml-small.bin (small, 487MB)",
        "language": "zh",
        "whisper_cli": str(WHISPER_CLI),
        "cli_exists": WHISPER_CLI.exists(),
        "model_exists": WHISPER_Model.exists(),
        "ffmpeg": str(FFMPEG),
        "temp_dir": str(TEMP_DIR),
    }
