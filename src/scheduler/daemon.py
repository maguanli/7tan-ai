"""
守护进程模块 — Windows Service / Linux daemon 支持
详见架构文档 §13 / §18
"""
import os
import sys
import signal
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional

from loguru import logger


# ============================================================
# 统一优雅重启 (§13) — Web API 和 AI 工具共用
# ============================================================

def graceful_restart(delay_seconds: int = 2, close_browser_flag: bool = True):
    """
    统一优雅重启函数
    
    供两处调用:
    - Web API:  POST /api/settings/restart → restart_self()
    - AI 工具:  self_restart() → self_modify_tools.py

    完整流程:
    1. 停止调度器（避免任务中断残留）
    2. 关闭浏览器（可选，由调用方决定）
    3. 释放数据库连接池（避免 SQLite 损坏）
    4. 保存运行状态到磁盘
    4.5 关闭服务器 socket（释放端口，让新进程能立即绑定）
    5. 启动新进程
    6. 轮询验证新进程健康（最多 35 秒）
    7. 退出当前进程
    """
    logger.info("🔄 正在优雅重启...")

    # ===== 阶段 0: 防重复重启锁 =====
    lock_file = _get_project_root() / "data" / ".restart_lock"
    if lock_file.exists():
        try:
            old_pid = int(lock_file.read_text().strip())
            os.kill(old_pid, 0)
            logger.warning(f"⚠️ 已有重启进行中 (PID={old_pid})，跳过")
            return
        except (ValueError, OSError):
            try:
                lock_file.unlink()
            except Exception:
                pass
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(str(os.getpid()))

    # ===== 阶段 1: 停止调度器 =====
    try:
        from src.scheduler.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("⏰ 调度器已停止")
    except Exception as e:
        logger.warning(f"调度器停止失败（继续重启）: {e}")

    # ===== 阶段 2: 关闭浏览器 =====
    if close_browser_flag:
        try:
            from src.tools.browser_tools import close_browser
            close_browser()
            logger.info("🌐 浏览器已关闭")
        except Exception:
            pass  # 浏览器可能未启动

    # ===== 阶段 3: 释放数据库连接池 =====
    try:
        from src.database.db import _engine as _db_engine
        if _db_engine:
            _db_engine.dispose()
            logger.info("💾 数据库连接池已释放")
    except Exception as e:
        logger.warning(f"数据库关闭失败（继续重启）: {e}")

    # ===== 阶段 4: 保存运行状态 =====
    try:
        _save_state()
        logger.info("💾 运行状态已保存")
    except Exception as e:
        logger.warning(f"状态保存失败（继续重启）: {e}")

    # ===== 阶段 4.5: 关闭服务器 socket，释放端口 =====
    try:
        from src.web.server import shutdown_server
        shutdown_server()
        logger.info("🔌 服务器端口已释放")
    except Exception as e:
        logger.warning(f"关闭服务器失败（继续重启）: {e}")

    # ===== 阶段 4.6: 释放本进程持有的单实例锁（让新进程能立即获取）=====
    # 单实例锁由 main.py 用 msvcrt 文件锁持有，进程退出才自动释放。
    # 但优雅重启是「先 spawn 新进程、后 os._exit 旧进程」，新进程启动时
    # 旧进程仍持锁会误判「已有实例」而退出。这里在 spawn 前 unlink 锁文件，
    # 新进程 os.open 会创建新文件并成功加锁（旧进程 fd 仍指向已 unlink 的 inode）。
    try:
        _lock_name = ".instance.lock"
        _argv = sys.argv[1:]
        if "--web" in _argv or "web" in _argv:
            _port = 9900
            try:
                for _i, _a in enumerate(_argv):
                    if _a in ("--port", "-p") and _i + 1 < len(_argv):
                        _port = int(_argv[_i + 1])
                        break
            except (ValueError, IndexError):
                _port = 9900
            _lock_name = f".instance.lock.web{_port}"
        _lp = _get_project_root() / "data" / _lock_name
        if _lp.exists():
            _lp.unlink()
            logger.info(f"🔓 已释放单实例锁: {_lock_name}")
    except Exception as _e:
        logger.debug(f"释放单实例锁跳过: {_e}")

    # ===== 阶段 5: 启动新进程 =====
    if getattr(sys, 'frozen', False):
        cmd = [sys.executable, *sys.argv[1:]]
    else:
        script_path = Path(sys.argv[0]).resolve()
        if not script_path.exists():
            script_path = _get_project_root() / "main.py"
        cmd = [sys.executable, str(script_path), *sys.argv[1:]]

    logger.info(f"🔄 启动新进程: {' '.join(cmd)}")

    try:
        if os.name == 'nt':
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        else:
            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        logger.info("✅ 新进程已启动")
    except Exception as e:
        logger.error(f"❌ 启动新进程失败: {e}")
        _cleanup_lock(lock_file)
        return

    # ===== 阶段 6: 验证新进程健康 =====
    port = _get_server_port()
    time.sleep(delay_seconds)

    if _verify_new_process(port):  # 默认 timeout=35，端口已释放通常几秒内就绪
        logger.info("✅ 新进程健康检查通过")
    else:
        logger.warning("⚠️ 新进程健康检查超时（可能端口未就绪），继续退出")

    # ===== 阶段 7: 清理锁并退出 =====
    _cleanup_lock(lock_file)
    os._exit(0)


def restart_self():
    """
    Web API 重启入口
    
    由 POST /api/settings/restart 调用。
    关闭浏览器后重启（前端用户可见操作）。
    """
    graceful_restart(delay_seconds=2, close_browser_flag=True)


def _cleanup_lock(lock_file: Path):
    """安全删除重启锁文件"""
    try:
        if lock_file.exists():
            lock_file.unlink()
    except Exception:
        pass


def cleanup_stale_restart_locks():
    """
    启动时清理残留的重启锁文件。
    如果锁中的 PID 已不存在，则安全删除。
    """
    lock_file = _get_project_root() / "data" / ".restart_lock"
    if not lock_file.exists():
        return
    try:
        old_pid = int(lock_file.read_text().strip())
        os.kill(old_pid, 0)  # 检查是否存活
        logger.debug(f"重启锁有效 (PID={old_pid})，保留")
    except (ValueError, OSError):
        # PID 无效或进程已死，清理
        _cleanup_lock(lock_file)
        logger.info("🧹 已清理残留的重启锁文件")


def _save_state():
    """保存关键运行状态到 data/state.json（使用项目根绝对路径）"""
    from datetime import datetime
    import json

    state = {
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid(),
    }

    state_path = _get_project_root() / "data" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _get_project_root() -> Path:
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def _get_server_port() -> int:
    """从配置文件读取服务器端口，默认 9800
    
    优先读取 web.port（config.yaml 标准键），
    同时兼容 server.port（旧版配置）。
    """
    try:
        from src.config.loader import load_config
        config = load_config()
        # 优先 web.port（当前 config.yaml 实际键名）
        web_port = config.get("web", {}).get("port")
        if web_port is not None:
            return int(web_port)
        # 兼容旧版 server.port
        server_port = config.get("server", {}).get("port")
        if server_port is not None:
            return int(server_port)
        return 9800
    except Exception:
        return 9800


def _verify_new_process(port: int, timeout: int = 35) -> bool:
    """
    轮询验证新进程是否成功启动
    
    通过 GET /api/health 检查，每秒一次，直到超时。
    不仅检查 200 状态码，还验证响应体包含 "ok" 状态，
    防止端口被非 7Tan 进程占用时误判。
    返回 True 表示新进程已就绪。
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/health",
                method="GET",
            )
            resp = urllib.request.urlopen(req, timeout=2)
            if resp.status == 200:
                body = resp.read().decode("utf-8", errors="replace")
                # 验证响应确实是 7Tan 的 /api/health（返回 {"status":"ok",...}）
                if '"status"' in body or '"ok"' in body.lower():
                    return True
                logger.debug(f"健康检查响应异常: {body[:100]}")
        except Exception:
            pass
        time.sleep(1)
    return False


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
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                if self.is_running():
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.5)
                logger.info(f"🛑 守护进程已停止 (PID: {pid})")
            except OSError:
                pass
        self._remove_pidfile()

    def _setup_signal_handlers(self):
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
            main_func: 主循环回调函数，应返回 True 继续或 False 退出
        """
        self._setup_signal_handlers()
        self._write_pidfile()
        logger.info(f"🛡️ 守护进程已启动 (PID: {os.getpid()})")

        try:
            while self._running:
                try:
                    result = main_func(*args, **kwargs)
                    if result is False:
                        break
                except Exception as e:
                    logger.error(f"守护进程主循环异常: {e}")
                    time.sleep(5)
        except KeyboardInterrupt:
            logger.info("收到键盘中断")
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
