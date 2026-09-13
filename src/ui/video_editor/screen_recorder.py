"""
视频剪辑器 — 录屏核心（Phase 4）

技术架构（参见架构文档 8.1）：
    屏幕 ──→ mss (30fps截图) ──┐
    系统音频 ──→ WASAPI loopback ──→ FFmpeg 管道 ──→ MP4
    麦克风 ──→ PyAudio ──→ [增益 x0.8] ──┘

三种录制模式：全屏 / 区域 / 窗口
"""

import subprocess
import threading
import time
import os
import re
import atexit
from pathlib import Path
from typing import Optional, Callable

import mss
import numpy as np
from loguru import logger

from src.ui.video_editor.data_models import RecordingConfig
from src.ui.video_editor.config import (
    RECORDING_DEFAULT_FPS, RECORDING_DEFAULT_CODEC,
    RECORDING_DEFAULT_QUALITY, RECORDING_MIN_DISK_GB,
    FFMPEG_PATH,
)
from src.ui.video_editor.utils import human_readable_size


class ScreenRecorder:
    """录屏核心引擎

    使用 mss 捕获屏幕 + FFmpeg 管道编码，支持系统音频和麦克风混合。
    """

    def __init__(self):
        self._config: Optional[RecordingConfig] = None
        self._process: Optional[subprocess.Popen] = None
        self._running = False
        self._paused = False
        self._start_time: float = 0.0
        self._elapsed: float = 0.0
        self._frame_count: int = 0
        self._thread: Optional[threading.Thread] = None

        # 回调
        self.on_time_updated: Optional[Callable[[float], None]] = None
        self.on_state_changed: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_audio_warning: Optional[Callable[[str], None]] = None  # 音频不可用警告

        # 音频状态（供 UI 提示）
        self._audio_warning: Optional[str] = None

        # 注册退出清理，防止孤儿 ffmpeg 进程
        atexit.register(self._cleanup_on_exit)

    def __del__(self):
        """析构函数：确保 ffmpeg 子进程被终止"""
        self._kill_ffmpeg()

    @staticmethod
    def kill_orphan_ffmpeg() -> int:
        """检测并杀死所有孤儿 ffmpeg gdigrab 进程（供启动时调用）
        
        Returns:
            杀死的进程数量
        """
        import signal
        killed = 0
        try:
            result = subprocess.run(
                ['tasklist', '/fi', 'imagename eq ffmpeg.exe', '/fo', 'csv', '/nh'],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.strip().split('\n'):
                if 'ffmpeg.exe' in line.lower():
                    parts = line.replace('"', '').split(',')
                    if len(parts) >= 2:
                        pid_str = parts[1].strip()
                        try:
                            pid = int(pid_str)
                            os.kill(pid, signal.SIGTERM)
                            killed += 1
                            logger.info(f"已清理孤儿 ffmpeg 进程 (PID={pid})")
                        except (ValueError, OSError, PermissionError):
                            pass
        except Exception as e:
            logger.warning(f"清理孤儿 ffmpeg 失败: {e}")
        return killed

    def _cleanup_on_exit(self):
        """atexit 回调：程序退出时强制终止 ffmpeg"""
        self._running = False
        self._kill_ffmpeg()

    def _kill_ffmpeg(self):
        """强制终止 ffmpeg 子进程"""
        p = self._process
        if p is None:
            return
        try:
            if p.poll() is None:
                # 先尝试优雅退出
                try:
                    if p.stdin:
                        p.stdin.write(b'q')
                        p.stdin.flush()
                        p.stdin.close()
                except Exception:
                    pass
                # 等待 2 秒，不行就 kill
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()
                    try:
                        p.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                logger.info("ffmpeg 录制进程已清理")
        except Exception as e:
            logger.warning(f"清理 ffmpeg 失败: {e}")
        self._process = None

    # ==================================================================
    #  公共 API
    # ==================================================================

    def start(self, config: RecordingConfig) -> bool:
        """开始录制

        Args:
            config: 录屏配置

        Returns:
            True 表示成功启动
        """
        if self._running:
            logger.warning("已在录制中")
            return False

        # 磁盘检查
        if not self._check_disk_space(config.output_dir):
            if self.on_error:
                self.on_error("磁盘空间不足，至少需要 1GB 可用空间")
            return False

        # 预检 FFmpeg
        ok, err = self._check_ffmpeg_health()
        if not ok:
            if self.on_error:
                self.on_error(err)
            return False

        self._config = config
        self._running = True
        self._paused = False
        self._elapsed = 0.0
        self._frame_count = 0
        self._est_elapsed = 0.0  # gdigrab 模式估算时间
        self._audio_failed = False
        self._audio_warning = None

        try:
            self._process = self._build_ffmpeg_pipe(config)
        except Exception as e:
            self._running = False
            logger.error(f"启动 FFmpeg 失败: {e}")
            if self.on_error:
                self.on_error(f"FFmpeg 启动失败: {e}")
            return False

        # 🔍 启动验证：等待 0.5s 确认 ffmpeg 没有立即崩溃
        startup_check = 0.0
        while startup_check < 0.5:
            time.sleep(0.1)
            startup_check += 0.1
            if self._process.poll() is not None:
                # ffmpeg 已退出 → 音频设备可能不兼容，回退到仅录画面
                logger.warning(f"FFmpeg 启动失败 (exit={self._process.returncode})，尝试仅录画面...")
                # 重新启动，不带音频
                self._running = False
                try:
                    config_no_audio = RecordingConfig(
                        mode=config.mode,
                        fps=config.fps,
                        codec=config.codec,
                        quality=config.quality,
                        capture_system_audio=False,
                        capture_mic=False,
                        output_dir=config.output_dir,
                        region_rect=config.region_rect,
                    )
                    self._process = self._build_ffmpeg_pipe(config_no_audio)
                except Exception as e:
                    if self.on_error:
                        self.on_error(f"录制引擎启动失败: {e}")
                    return False
                self._config = config_no_audio
                self._running = True  # 回退成功，恢复运行状态
                config = config_no_audio  # 后续日志用新配置
                break

        # 监控 FFmpeg stderr
        self._stderr_thread = threading.Thread(
            target=self._monitor_stderr, daemon=True
        )
        self._stderr_thread.start()

        self._start_time = time.time()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        if self.on_state_changed:
            self.on_state_changed("recording")

        # 用实际生效配置（可能已回退为无音频）打印音频状态，避免误导
        actual = self._config or config
        audio_on = actual.capture_system_audio or actual.capture_mic
        logger.info(
            f"🎥 开始录制 — 模式={actual.mode}, "
            f"分辨率={actual.region_rect[2]}x{actual.region_rect[3]}, "
            f"fps={actual.fps}, 音频={'✅' if audio_on else '❌'}"
        )
        # 音频不可用 → 明确通知 UI，不再静默无声
        if not audio_on and self._audio_warning:
            logger.warning(f"[录屏] {self._audio_warning}")
            if self.on_audio_warning:
                try:
                    self.on_audio_warning(self._audio_warning)
                except Exception:
                    pass
        return True

    def pause(self):
        """暂停录制"""
        if self._running and not self._paused:
            self._paused = True
            self._elapsed += time.time() - self._start_time
            if self.on_state_changed:
                self.on_state_changed("paused")
            logger.info("⏸ 录制已暂停")

    def resume(self):
        """继续录制"""
        if self._running and self._paused:
            self._paused = False
            self._start_time = time.time()
            if self.on_state_changed:
                self.on_state_changed("recording")
            logger.info("▶ 录制已继续")

    def stop(self) -> Optional[str]:
        """停止录制

        Returns:
            录制完成的文件路径，失败返回 None
        """
        if not self._running:
            return None

        self._running = False
        self._paused = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        if hasattr(self, '_stderr_thread') and self._stderr_thread and self._stderr_thread.is_alive():
            self._stderr_thread.join(timeout=3.0)

        output_path = self._finalize()
        self._process = None

        if self.on_state_changed:
            self.on_state_changed("stopped")

        if output_path and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            logger.info(f"✅ 录制完成: {output_path} ({human_readable_size(size)})")
            return output_path
        else:
            logger.error("录制失败，未生成有效文件")
            return None

    @property
    def is_recording(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def elapsed(self) -> float:
        """录制时长（秒）"""
        if not self._running:
            return self._elapsed
        if self._paused:
            return self._elapsed
        return self._elapsed + (time.time() - self._start_time)

    @property
    def frame_count(self) -> int:
        return self._frame_count

    # ==================================================================
    #  内部实现
    # ==================================================================

    def _check_disk_space(self, output_dir: str) -> bool:
        """检查磁盘空间"""
        try:
            import shutil
            usage = shutil.disk_usage(output_dir or os.getcwd())
            free_gb = usage.free / (1024 ** 3)
            if free_gb < RECORDING_MIN_DISK_GB:
                logger.warning(f"磁盘空间不足: {free_gb:.1f}GB < {RECORDING_MIN_DISK_GB}GB")
                return False
            return True
        except Exception:
            return True  # 无法检查时放行

    def _build_ffmpeg_pipe(self, config: RecordingConfig) -> subprocess.Popen:
        """构建 FFmpeg 子进程（gdigrab 抓屏 + dshow 音频输入）
        
        修复：根据 RecordingConfig 的 capture_system_audio / capture_mic
        动态添加音频输入，不再硬编码 -an。
        """
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"

        # 输出路径
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = config.output_dir or os.path.join(os.getcwd(), "recordings")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"recording_{timestamp}.mp4")
        # 用 MKV 避免异常退出导致文件损坏
        output_file = output_file.replace(".mp4", ".mkv")

        x, y, w, h = config.region_rect

        # ==================== 视频输入 ====================
        cmd = [ffmpeg, "-y"]

        if config.mode == "region":
            cmd += [
                "-f", "gdigrab", "-framerate", str(config.fps),
                "-offset_x", str(x), "-offset_y", str(y),
                "-video_size", f"{w}x{h}",
                "-i", "desktop",
            ]
        else:
            cmd += [
                "-f", "gdigrab", "-framerate", str(config.fps),
                "-video_size", f"{w}x{h}",
                "-i", "desktop",
            ]

        # ==================== 音频输入 ====================
        audio_inputs = []   # 标签如 "[1:a]", "[2:a]"
        audio_devices_failed = []
        mic_input_label = None  # 麦克风音频流标签

        if config.capture_system_audio:
            try:
                loopback_dev = self._detect_loopback_device()
                # 候选设备：alternative名 → 完整名 → 常见简称（多级尝试，防简称打不开）
                candidates = []
                if loopback_dev:
                    candidates.append(loopback_dev)
                for extra in ("audio=立体声混音", "audio=Stereo Mix",
                              "audio=What U Hear", "audio=Wave Out Mix"):
                    if extra not in candidates:
                        candidates.append(extra)

                used_dev = None
                for dev in candidates:
                    ok, _ = self._check_audio_device(dev)
                    if ok:
                        used_dev = dev
                        break
                if used_dev:
                    cmd += ["-f", "dshow", "-i", used_dev,
                            "-thread_queue_size", "4096"]
                    audio_inputs.append(f"[{len(audio_inputs) + 1}:a]")
                    logger.info(f"系统音频: {used_dev}")
                else:
                    audio_devices_failed.append("系统音频(全部候选不可用)")
                    self._audio_warning = (
                        "未检测到可用的系统音频捕获设备（立体声混音/Stereo Mix），"
                        "本次录制将仅保留画面。请在系统声音设置中启用“立体声混音”。"
                    )
                    logger.warning(self._audio_warning)
            except Exception as e:
                audio_devices_failed.append(f"系统音频({e})")
                logger.warning(f"系统音频初始化失败: {e}")

        if config.capture_mic:
            try:
                mic_dev = self._detect_mic_device(config.mic_device_id)
                ok, _ = self._check_audio_device(mic_dev)
                if ok:
                    cmd += ["-f", "dshow", "-i", mic_dev,
                            "-thread_queue_size", "4096"]
                    audio_inputs.append(f"[{len(audio_inputs) + 1}:a]")
                    mic_input_label = audio_inputs[-1]  # 记录用于音量调节
                    logger.info(f"麦克风: {mic_dev} (音量={config.mic_volume:.0%})")
                else:
                    audio_devices_failed.append(f"麦克风({mic_dev})")
                    logger.warning(f"麦克风设备不可用: {mic_dev}")
            except Exception as e:
                audio_devices_failed.append(f"麦克风({e})")
                logger.warning(f"麦克风初始化失败: {e}")

        if audio_devices_failed:
            logger.warning(
                f"以下音频设备不可用，将仅录制画面: {', '.join(audio_devices_failed)}"
            )
            # 音频失败非致命错误，不触发 on_error 避免隐藏录屏 overlay

        audio_enabled = len(audio_inputs) > 0

        # ==================== 编码参数 ====================
        cmd += ["-c:v", config.codec, "-crf", str(config.quality),
                "-preset", "ultrafast", "-pix_fmt", "yuv420p"]

        # ==================== 音频处理 ====================
        if audio_enabled:
            if len(audio_inputs) > 1:
                # 多路音频 → amix 混合（有麦克风时先调音量再混合）
                if mic_input_label and config.capture_mic:
                    # [1:a]volume=0.8[mic];[mic][2:a]amix=...[aout]
                    other = [a for a in audio_inputs if a != mic_input_label]
                    fc = (f"{mic_input_label}volume={config.mic_volume}[mic];"
                          f"[mic]{''.join(other)}amix=inputs={len(audio_inputs)}"
                          f":duration=first:dropout_transition=2[aout]")
                else:
                    amix_src = "".join(audio_inputs)
                    fc = f"{amix_src}amix=inputs={len(audio_inputs)}:duration=first:dropout_transition=2[aout]"
                cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
                        "-c:a", "aac", "-b:a", "128k"]
            else:
                # 单路音频：直接映射输入流（不用 filter label 方括号语法）
                audio_idx = len(cmd) - sum(1 for a in cmd if a.startswith("-i"))
                # 更简单：视频是第一个 -i，音频是第二个 -i
                if mic_input_label and config.capture_mic:
                    cmd += ["-af", f"volume={config.mic_volume}"]
                cmd += ["-map", "0:v", "-map", "1:a",
                        "-c:a", "aac", "-b:a", "128k"]
            logger.info(f"音频: 已启用 ({len(audio_inputs)}路)")
        else:
            cmd += ["-an"]
            logger.info("音频: 已关闭")

        cmd.append(output_file)
        logger.info(f"FFmpeg 录制命令: {' '.join(cmd)}")

        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def _detect_loopback_device(self) -> Optional[str]:
        """自动检测 Windows 系统音频捕获设备（结果缓存）

        修复录屏无声：ffmpeg dshow 必须使用「完整设备名」或 alternative name，
        硬编码的简称（audio=立体声混音）打不开设备 → 之前总是静默无声。
        现在依次尝试：
          1. alternative name（纯 ASCII @device_cm_...\\wave_...，最稳）
          2. 完整设备名（优先含 混音/Stereo Mix/loopback 的 audio 设备）
          3. 列表中的第一个 audio 设备
        全部失败返回 None（由调用方明确提示，不再静默降级）。
        """
        if hasattr(self, '_cached_loopback'):
            return self._cached_loopback
        self._cached_loopback = None
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"
        try:
            result = subprocess.run(
                [ffmpeg, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True, timeout=6, creationflags=subprocess.CREATE_NO_WINDOW
            )
            raw = (result.stderr or b"") + (result.stdout or b"")
            # 双编码解码：ffmpeg 不同版本可能输出 UTF-8 或 GBK
            stderr = ""
            for enc in ("utf-8", "gbk", "latin-1"):
                try:
                    stderr = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if not stderr:
                stderr = raw.decode("utf-8", "replace")

            # 1) alternative name（音频设备格式 @device_cm_{...}\wave_{...}）
            for line in stderr.splitlines():
                if "@device_cm_" in line and "wave_" in line:
                    m = re.search(r'@device_cm_[^\s"\']+', line)
                    if m:
                        self._cached_loopback = f"audio={m.group(0)}"
                        logger.info(f"系统音频设备(alternative): {self._cached_loopback}")
                        return self._cached_loopback

            # 2) 完整设备名：优先混音类，其次任意 audio 设备
            pref = None
            first_audio = None
            for line in stderr.splitlines():
                if '"' not in line:
                    continue
                name = line.split('"')[1]
                if not name or "dshow" in name.lower():
                    continue
                if "(audio)" in line or "(Audio)" in line:
                    if first_audio is None:
                        first_audio = name
                    low = name.lower()
                    if ("混音" in name or "stereo mix" in low or "loopback" in low
                            or "what u hear" in low or "wave out mix" in low):
                        pref = name
                        break
            if pref:
                self._cached_loopback = f"audio={pref}"
                logger.info(f"系统音频设备(全名): {self._cached_loopback}")
                return self._cached_loopback
            if first_audio:
                self._cached_loopback = f"audio={first_audio}"
                logger.info(f"系统音频设备(首个audio): {self._cached_loopback}")
                return self._cached_loopback
        except Exception as e:
            logger.warning(f"检测系统音频设备异常: {e}")
        logger.warning("未检测到任何系统音频捕获设备")
        return None

    def _detect_mic_device(self, device_id: Optional[int] = None) -> str:
        """自动检测麦克风 dshow 设备名（结果缓存）"""
        if hasattr(self, '_cached_mic'):
            return self._cached_mic
        if device_id is not None:
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                info = p.get_device_info_by_index(device_id)
                p.terminate()
                name = info.get("name", "")
                if name:
                    self._cached_mic = f"audio={name}"
                    return self._cached_mic
            except Exception:
                pass
        try:
            result = subprocess.run(
                [str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg",
                 "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=3, creationflags=subprocess.CREATE_NO_WINDOW
            )
            stderr = (result.stderr or "") + (result.stdout or "")
            for line in stderr.split("\n"):
                line_lower = line.strip().lower()
                if "microphone" in line_lower or "mic" in line_lower or "麦克风" in line:
                    if '"' in line:
                        dev = line.split('"')[1]
                        self._cached_mic = f"audio={dev}"
                        return self._cached_mic
        except Exception:
            pass
        return "audio=麦克风"

    def _get_mic_device_name(self, device_id: Optional[int]) -> str:
        """获取麦克风设备名称（简化实现）"""
        if device_id is not None:
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                info = p.get_device_info_by_index(device_id)
                p.terminate()
                return info.get("name", f"设备{device_id}")
            except Exception:
                pass
        return "默认设备"

    def _check_ffmpeg_health(self) -> tuple[bool, str]:
        """预检：FFmpeg 是否能正常工作
        Returns: (ok, error_message)
        """
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"
        try:
            result = subprocess.run(
                [ffmpeg, "-version"],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=10, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode != 0:
                return False, f"FFmpeg 无法运行: {result.stderr[:200]}"
            return True, ""
        except FileNotFoundError:
            return False, "FFmpeg 未找到！请安装 FFmpeg 或将其加入 PATH"
        except Exception as e:
            return False, f"FFmpeg 检测失败: {e}"

    def _check_audio_device(self, device_spec: str) -> tuple[bool, str]:
        """预检：dshow 音频设备是否可用
        
        Args:
            device_spec: 如 "audio=立体声混音"
        Returns:
            (ok, error_message)
        """
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"
        try:
            # 用 -t 0.1 快速测试能否打开设备
            result = subprocess.run(
                [ffmpeg, "-y", "-f", "dshow", "-i", device_spec,
                 "-t", "0.2", "-f", "null", "-"],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=6, creationflags=subprocess.CREATE_NO_WINDOW
            )
            stderr = (result.stderr or "") + (result.stdout or "")
            stderr_lower = stderr.lower()
            # non-zero exit = device not available
            if result.returncode != 0:
                logger.debug(f"audio device check failed [{device_spec}]: exit={result.returncode}")
                return False, stderr[:200] if stderr else f"device not available (exit={result.returncode})"
            if ("could not" in stderr_lower or "cannot" in stderr_lower or
                    "no such" in stderr_lower or "input/output error" in stderr_lower):
                return False, stderr[:200]
            return True, ""
        except subprocess.TimeoutExpired:
            # 超时意味着设备打开了但卡住了，也算不可用
            return False, "设备检测超时"
        except Exception as e:
            return False, str(e)

    def _monitor_stderr(self):
        """Monitor FFmpeg stderr, detect audio device failures etc."""
        if not self._process or not self._process.stderr:
            return
        self._last_stderr_lines = ""
        try:
            for line in iter(self._process.stderr.readline, b""):
                if not self._running:
                    break
                try:
                    text = line.decode("utf-8", errors="replace").strip()
                except Exception:
                    continue
                if not text:
                    continue
                # Save last lines for crash diagnosis
                self._last_stderr_lines = (self._last_stderr_lines + "\n" + text)[-2000:]
                # Only alert on real error keywords, skip status lines
                lower = text.lower()
                is_fatal = any(kw in lower for kw in [
                    "cannot open audio", "cannot find audio",
                    "input/output error", "immediate exit",
                    "permission denied", "device is already in use",
                ])
                is_status_line = any(kw in lower for kw in [
                    "frame=", "fps=", "speed=", "size=", "time=",
                    "bitrate=", "q=", "l size=",
                ])
                if is_fatal:
                    logger.warning(f"[FFmpeg error] {text}")
                    if not getattr(self, "_audio_failed", False):
                        self._audio_failed = True
                        if self.on_error:
                            self.on_error(f"Recording error: {text[:150]}")
                elif is_status_line:
                    logger.debug(f"[FFmpeg] {text}")
                else:
                    logger.debug(f"[FFmpeg] {text}")
        except (BrokenPipeError, ValueError, OSError):
            pass

    def _capture_loop(self):
        """监控 ffmpeg 进程（gdigrab 模式无需手动截图）"""
        if not self._process or not self._config:
            return

        fps = self._config.fps
        frame_interval = 1.0 / fps
        last_update = 0.0

        while self._running and self._process.poll() is None:
            if not self._paused:
                self._frame_count += 1
                # 每 0.5s 更新一次时间（而非 30 帧）
                now = time.time()
                if self._start_time and now - last_update >= 0.5:
                    self._est_elapsed = now - self._start_time
                    if self.on_time_updated:
                        self.on_time_updated(self._est_elapsed)
                    last_update = now
            time.sleep(frame_interval)

        # ffmpeg process exited
        exit_code = self._process.returncode if self._process else -1
        # 如果是用户主动停止，不要报错
        if not self._running:
            return
        stderr_output = ""
        if exit_code != 0 and self._process and self._process.stderr:
            try:
                remaining = self._process.stderr.read()
                stderr_output = remaining.decode('utf-8', errors='replace')
            except Exception:
                pass
            # Also try to read any stderr from _monitor_stderr (which may have consumed it)
            if not stderr_output.strip():
                stderr_output = getattr(self, '_last_stderr_lines', "")
            logger.error(f"FFmpeg crashed (exit={exit_code}): {stderr_output[:500]}")
            if self.on_error and self._frame_count < 60:
                # Only show error if crash happened early (first ~2s at 30fps)
                if stderr_output.strip():
                    self.on_error(f"Recording crashed (exit={exit_code}): {stderr_output[:200]}")
                else:
                    self.on_error(f"Recording crashed (exit={exit_code}). Check logs for details.")
        self._running = False

    def _get_monitor(self, sct) -> dict:
        """根据配置获取 mss 监视器参数"""
        config = self._config
        if not config:
            return sct.monitors[1]  # 默认主屏

        if config.mode == "region":
            x, y, w, h = config.region_rect
            return {"left": x, "top": y, "width": w, "height": h}
        elif config.mode == "window":
            # 窗口模式：通过窗口标题定位
            if config.window_title:
                try:
                    import ctypes
                    from ctypes import wintypes
                    hwnd = ctypes.windll.user32.FindWindowW(None, config.window_title)
                    if hwnd:
                        rect = wintypes.RECT()
                        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        return {
                            "left": rect.left,
                            "top": rect.top,
                            "width": rect.right - rect.left,
                            "height": rect.bottom - rect.top,
                        }
                except Exception:
                    pass
            # 降级为全屏
            return sct.monitors[1]
        else:
            # fullscreen：使用主显示器
            return sct.monitors[1]

    def _finalize(self) -> Optional[str]:
        """优雅停止 ffmpeg 并获取输出文件"""
        if not self._process:
            return None

        # 发送 'q' 让 ffmpeg 正常结束（写入 moov atom）
        try:
            if self._process.stdin:
                self._process.stdin.write(b'q')
                self._process.stdin.flush()
                self._process.stdin.close()
        except Exception:
            pass

        try:
            self._process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()

        # 从命令中提取输出路径
        if self._process.args:
            for arg in reversed(self._process.args):
                if arg.endswith(".mkv") or arg.endswith(".mp4"):
                    return arg
        return None


# ==================================================================
#  便捷函数
# ==================================================================

def get_available_mics() -> list[dict]:
    """获取可用麦克风列表

    Returns:
        [{"index": 0, "name": "麦克风 (Realtek)"}, ...]
    """
    mics = []
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                mics.append({
                    "index": i,
                    "name": info.get("name", f"设备 {i}"),
                })
        p.terminate()
    except ImportError:
        logger.warning("PyAudio 未安装，无法枚举麦克风")
    except Exception as e:
        logger.error(f"枚举麦克风失败: {e}")

    return mics


def check_wasapi_available() -> bool:
    """检查系统音频捕获设备（立体声混音/任何 audio 设备）是否可用"""
    try:
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"
        result = subprocess.run(
            [ffmpeg, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW
        )
        raw = (result.stderr or b"") + (result.stdout or b"")
        for enc in ("utf-8", "gbk", "latin-1"):
            try:
                stderr = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            stderr = raw.decode("utf-8", "replace")
        return ("立体声混音" in stderr or "Stereo Mix" in stderr
                or ("@device_cm_" in stderr and "wave_" in stderr))
    except Exception:
        return False
