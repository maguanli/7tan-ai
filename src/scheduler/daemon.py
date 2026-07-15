"""
守护进程模块 — Windows Service / Linux daemon 支持
详见架构文档 §13 / §18
"""
import os
import sys
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

from loguru import logger


# ============================================================
# 自重启 (§13)
# ============================================================

def restart_self():
    """
    Python 进程优雅重启

    工作流:
    1. 保存当前状态到磁盘
    2. 关闭所有资源（浏览器/数据库连接）
    3. 启动新进程（subprocess.Popen）
    4. 退出当前进程

    局限性见 §13.2
    """
    logger.info("🔄 正在重启...")

    # 1. 保存状态
    try:
        _save_state()
    except Exception as e:
        logger.warning(f"状态保存失败（继续重启）: {e}")

    # 2. 关闭资源
    try:
        from src.tools.browser_tools import close_browser
        close_browser()
    except Exception:
        pass  # 浏览器可能未启动，忽略关闭异常

    # 3. 启动新进程
    if getattr(sys, 'frozen', False):
        exe = sys.executable
        args = sys.argv[1:]
    else:
        exe = sys.executable
        args = [sys.argv[0], *sys.argv[1:]]

    try:
        subprocess.Popen(
            [exe, *args],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=True,
        )
        logger.info("✅ 新进程已启动，即将退出")
        # 给新进程一点时间初始化
        time.sleep(1)
    except Exception as e:
        logger.error(f"❌ 启动新进程失败: {e}")

    # 4. 退出
    os._exit(0)


def _save_state():
    """保存关键运行状态"""
    from datetime import datetime
    import json

    state = {
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid(),
    }

    state_path = Path("data/state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ============================================================
# 守护进程管理 (§18.1)
# ============================================================

class Daemon:
    """
    守护进程管理器

    Windows: 使用 CREATE_NEW_PROCESS_GROUP + 信号处理
    Linux:   使用 fork + setsid 双叉法
    """

    def __init__(self, pidfile: str = "data/daemon.pid"):
        self.pidfile = Path(pidfile)
        self._running = True

    # ----- Linux daemonize -----

    def daemonize(self):
        """Linux 双叉守护进程化"""
        if os.name != "posix" or sys.platform == "darwin":
            return

        try:
            # 第一次 fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # 父进程退出
        except OSError as e:
            logger.error(f"第一次 fork 失败: {e}")
            sys.exit(1)

        # 脱离终端
        os.setsid()

        # 第二次 fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"第二次 fork 失败: {e}")
            sys.exit(1)

        # 重定向标准文件描述符
        sys.stdout.flush()
        sys.stderr.flush()
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, sys.stdin.fileno())
        os.dup2(devnull, sys.stdout.fileno())
        os.dup2(devnull, sys.stderr.fileno())
        os.close(devnull)

        # 写 PID 文件
        self._write_pidfile()
        logger.info(f"🐧 守护进程已启动 (PID: {os.getpid()})")

    # ----- 通用管理 -----

    def _write_pidfile(self):
        self.pidfile.parent.mkdir(parents=True, exist_ok=True)
        self.pidfile.write_text(str(os.getpid()))

    def _remove_pidfile(self):
        if self.pidfile.exists():
            self.pidfile.unlink()

    def get_pid(self) -> Optional[int]:
        """从 pidfile 读取 PID"""
        if self.pidfile.exists():
            return int(self.pidfile.read_text().strip())
        return None

    def is_running(self) -> bool:
        """检查守护进程是否在运行"""
        pid = self.get_pid()
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def stop(self):
        """停止守护进程"""
        pid = self.get_pid()
        if pid:
            try:
                if os.name == "nt":
                    os.kill(pid, signal.CTRL_BREAK_EVENT)
                else:
                    os.kill(pid, signal.SIGTERM)
                logger.info(f"🛑 已发送停止信号到 PID {pid}")
            except OSError as e:
                logger.error(f"停止进程失败: {e}")
        self._remove_pidfile()

    def setup_signal_handlers(self):
        """设置信号处理器"""
        def _handle_exit(signum, frame):
            logger.info(f"收到信号 {signum}，正在退出...")
            self._running = False
            self._remove_pidfile()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_exit)
        signal.signal(signal.SIGTERM, _handle_exit)

        if os.name == "nt":
            signal.signal(signal.SIGBREAK, _handle_exit)

    def run_forever(self, main_func, *args, **kwargs):
        """
        守护进程主循环

        Args:
            main_func: 主逻辑函数
            *args, **kwargs: 传递给 main_func 的参数
        """
        self.setup_signal_handlers()
        self._write_pidfile()

        logger.info(f"🏃 守护进程运行中 (PID: {os.getpid()})")

        try:
            main_func(*args, **kwargs)

            # 如果 main_func 返回，进入空闲循环
            while self._running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("👋 守护进程被中断")
        finally:
            self._cleanup()

    def _cleanup(self):
        """清理资源"""
        try:
            from src.tools.browser_tools import close_browser
            close_browser()
        except Exception:
            pass
        self._remove_pidfile()
        logger.info("🧹 守护进程已清理")


# ============================================================
# 无头模式 (§18.1)
# ============================================================

def setup_headless_mode():
    """配置无头模式环境变量，供浏览器模块读取"""
    os.environ["HEADLESS_MODE"] = "true"
    logger.info("👻 无头模式已启用")


def is_headless() -> bool:
    """检查是否在无头模式下运行"""
    return os.environ.get("HEADLESS_MODE", "").lower() == "true"
