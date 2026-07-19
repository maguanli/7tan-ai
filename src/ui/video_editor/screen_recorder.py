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

        self._config = config
        self._running = True
        self._paused = False
        self._elapsed = 0.0
        self._frame_count = 0

        try:
            self._process = self._build_ffmpeg_pipe(config)
        except Exception as e:
            self._running = False
            logger.error(f"启动 FFmpeg 失败: {e}")
            if self.on_error:
                self.on_error(f"FFmpeg 启动失败: {e}")
            return False

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
        """构建 FFmpeg 子进程管道"""
        ffmpeg = str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"

        # 输出路径
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = config.output_dir or os.path.join(os.getcwd(), "recordings")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"recording_{timestamp}.mp4")

        # 输入参数
        w, h = config.region_rect[2], config.region_rect[3]
        cmd = [
            ffmpeg,
            "-y",                           # 覆盖输出
            "-f", "rawvideo",               # 原始视频流
            "-vcodec", "rawvideo",
            "-s", f"{w}x{h}",               # 分辨率
            "-pix_fmt", "bgra",             # mss 输出格式
            "-r", str(config.fps),          # 帧率
            "-i", "-",                      # stdin 输入
        ]

        # 系统音频输入（WASAPI loopback）
        if config.capture_system_audio:
            cmd += [
                "-f", "dshow",
                "-i", "audio=立体声混音",     # Windows WASAPI
            ]
        elif config.capture_mic:
            # 仅麦克风时仍需音频输入占位
            cmd += [
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
            ]

        # 麦克风输入
        if config.capture_mic and config.capture_system_audio:
            # 系统音频 + 麦克风 → FFmpeg 混音
            mic_device = f"audio=麦克风 ({self._get_mic_device_name(config.mic_device_id)})"
            cmd += [
                "-f", "dshow",
                "-i", mic_device,
                "-filter_complex",
                "[1:a][2:a]amix=inputs=2:duration=first:weights=1 0.8[outa]",
            ]
            audio_map = ["-map", "0:v", "-map", "[outa]"]
        elif config.capture_mic:
            mic_device = f"audio=麦克风 ({self._get_mic_device_name(config.mic_device_id)})"
            cmd += [
                "-f", "dshow",
                "-i", mic_device,
            ]
            audio_map = ["-map", "0:v", "-map", "1:a"]
        elif config.capture_system_audio:
            audio_map = ["-map", "0:v", "-map", "1:a"]
        else:
            audio_map = ["-map", "0:v"]

        # 编码参数
        cmd += audio_map
        cmd += [
            "-c:v", config.codec,
            "-crf", str(config.quality),
            "-preset", "ultrafast",         # 录屏优先速度
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_file,
        ]

        logger.debug(f"FFmpeg 命令: {' '.join(cmd)}")

        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

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

    def _capture_loop(self):
        """主捕获循环（在子线程中运行）"""
        if not self._process or not self._process.stdin:
            return

        fps = self._config.fps if self._config else RECORDING_DEFAULT_FPS
        frame_interval = 1.0 / fps

        with mss.mss() as sct:
            monitor = self._get_monitor(sct)

            while self._running:
                loop_start = time.time()

                if not self._paused:
                    try:
                        # 截图
                        img = sct.grab(monitor)
                        # 写入 FFmpeg stdin
                        self._process.stdin.write(img.bgra)
                        self._frame_count += 1
                    except (BrokenPipeError, OSError) as e:
                        logger.error(f"写入 FFmpeg 管道失败: {e}")
                        if self.on_error:
                            self.on_error(f"录制中断: {e}")
                        self._running = False
                        break
                    except Exception as e:
                        logger.error(f"截屏失败: {e}")
                        if self.on_error:
                            self.on_error(f"截屏失败: {e}")

                # 时间回调
                if self.on_time_updated:
                    self.on_time_updated(self.elapsed)

                # 帧率控制
                elapsed_frame = time.time() - loop_start
                sleep_time = frame_interval - elapsed_frame
                if sleep_time > 0:
                    time.sleep(sleep_time)

        # 安全关闭 stdin
        try:
            if self._process and self._process.stdin:
                self._process.stdin.close()
        except Exception:
            pass

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
        """等待 FFmpeg 完成编码"""
        if not self._process:
            return None

        try:
            self._process.stdin.close()
        except Exception:
            pass

        try:
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg 超时，强制终止")
            self._process.kill()
            self._process.wait()

        # 从命令中提取输出路径
        if self._process.args:
            # args 是列表，输出文件是最后一个非选项参数
            for arg in reversed(self._process.args):
                if not arg.startswith("-") and arg.endswith(".mp4"):
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
