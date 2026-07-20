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

        try:
            self._process = self._build_ffmpeg_pipe(config)
        except Exception as e:
            self._running = False
            logger.error(f"启动 FFmpeg 失败: {e}")
            if self.on_error:
                self.on_error(f"FFmpeg 启动失败: {e}")
            return False

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

        logger.info(
            f"🎥 开始录制 — 模式={config.mode}, "
            f"分辨率={config.region_rect[2]}x{config.region_rect[3]}, "
            f"fps={config.fps}, 音频={'✅' if config.capture_system_audio else '❌'}"
        )
        return True

    def pause(self):
        """暂停录制"""
        if self._running and not self._paused:
            self._paused = True
            if self.on_state_changed:
                self.on_state_changed("paused")
            logger.info("⏸ 录制已暂停")

    def resume(self):
        """继续录制"""
        if self._running and self._paused:
            self._paused = False
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
        """构建 FFmpeg 子进程（gdigrab 直接抓屏，不占 Python GIL）"""
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"

        # 输出路径
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = config.output_dir or os.path.join(os.getcwd(), "recordings")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"recording_{timestamp}.mp4")

        x, y, w, h = config.region_rect

        if config.mode == "region":
            # gdigrab 区域录制
            cmd = [
                ffmpeg, "-y",
                "-f", "gdigrab", "-framerate", str(config.fps),
                "-offset_x", str(x), "-offset_y", str(y),
                "-video_size", f"{w}x{h}",
                "-i", "desktop",
            ]
        else:
            # 全屏
            cmd = [
                ffmpeg, "-y",
                "-f", "gdigrab", "-framerate", str(config.fps),
                "-video_size", f"{w}x{h}",
                "-i", "desktop",
            ]

        # 跳过音频（默认关闭），用 MKV 格式避免 kill 导致文件损坏
        output_file = output_file.replace(".mp4", ".mkv")
        cmd += [
            "-c:v", config.codec,
            "-crf", str(config.quality),
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",
            output_file,
        ]

        logger.debug(f"FFmpeg 命令: {' '.join(cmd)}")

        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,  # 保留 stdin 以便发送 'q' 优雅退出
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def _detect_loopback_device(self) -> str:
        """自动检测 Windows WASAPI 环回设备名（结果缓存）"""
        if hasattr(self, '_cached_loopback'):
            return self._cached_loopback
        candidates = [
            "audio=立体声混音",
            "audio=Stereo Mix",
            "audio=What U Hear",
            "audio=Wave Out Mix",
            "audio=Loopback",
        ]
        try:
            result = subprocess.run(
                [str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg",
                 "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True, text=True, timeout=3,
            )
            stderr = (result.stderr or "") + (result.stdout or "")
            for line in stderr.split("\n"):
                line_lower = line.strip().lower()
                if "stereo mix" in line_lower or "loopback" in line_lower or "立体声混音" in line:
                    if '"' in line:
                        dev = line.split('"')[1]
                        self._cached_loopback = f"audio={dev}"
                        return self._cached_loopback
        except Exception:
            pass
        self._cached_loopback = candidates[0]
        return self._cached_loopback

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
                capture_output=True, text=True, timeout=3,
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
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return False, f"FFmpeg 无法运行: {result.stderr[:200]}"
            return True, ""
        except FileNotFoundError:
            return False, "FFmpeg 未找到！请安装 FFmpeg 或将其加入 PATH"
        except Exception as e:
            return False, f"FFmpeg 检测失败: {e}"

    def _monitor_stderr(self):
        """监控 FFmpeg stderr，检测音频设备失败等错误"""
        if not self._process or not self._process.stderr:
            return
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
                logger.debug(f"[FFmpeg] {text}")
                # 检测音频设备打开失败
                lower = text.lower()
                if any(kw in lower for kw in [
                    "audio=", "dshow", "cannot open audio",
                    "cannot find audio", "microphone",
                    "cannot open", "no such", "input/output error",
                    "立体声混音", "immediate exit"
                ]):
                    logger.warning(f"[FFmpeg 音频] {text}")
                    if not getattr(self, "_audio_failed", False):
                        self._audio_failed = True
                        if self.on_error:
                            self.on_error(f"音频设备不可用: {text[:150]}")
        except (BrokenPipeError, ValueError, OSError):
            pass

    def _capture_loop(self):
        """监控 ffmpeg 进程（gdigrab 模式无需手动截图）"""
        if not self._process or not self._config:
            return

        fps = self._config.fps
        frame_interval = 1.0 / fps

        while self._running and self._process.poll() is None:
            if not self._paused:
                self._frame_count += 1
                if self._frame_count % 30 == 0 and self.on_time_updated:
                    self._est_elapsed += 30 * frame_interval
                    self.on_time_updated(self._est_elapsed)
            time.sleep(frame_interval)

        # ffmpeg 已退出
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
    """检查 WASAPI loopback 是否可用"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True, timeout=10,
        )
        return "立体声混音" in result.stderr or "Stereo Mix" in result.stderr
    except Exception:
        return False
