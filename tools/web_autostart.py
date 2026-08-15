# -*- coding: utf-8 -*-
"""
7Tan Web 服务开机自启管理器（产品级）

用法:
    python tools/web_autostart.py --install      # 配置开机自启（幂等，已配置则跳过）
    python tools/web_autostart.py --uninstall    # 取消开机自启
    python tools/web_autostart.py --status       # 查看自启状态 + 9900 端口状态
    python tools/web_autostart.py --launch       # 启动 9900 服务（端口已开则直接退出）

原理:
    - 写注册表 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
      （用户级自启，无需管理员权限，开机自动后台运行）
    - 自启条目指向本脚本 --launch：内部以 pythonw 无窗口启动 main.py --web
    - 与桌面版单实例保护兼容（main.py 对 web 模式放行，可共存）
"""
import os
import sys
import time
import socket
import shutil
import subprocess

APP_NAME = "7TanWebService"
DEFAULT_PORT = 9900
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# 项目根目录（兼容源码与 PyInstaller 打包两种场景）
if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAIN_PY = os.path.join(ROOT, "main.py")
LOG_DIR = os.path.join(ROOT, "logs")
SELF_LOG = os.path.join(LOG_DIR, "web_autostart.log")
SERVICE_LOG = os.path.join(LOG_DIR, "web_9900.log")


def log(msg: str):
    """写日志 + 控制台输出（pythonw 下控制台无输出，日志兜底）"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(SELF_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    except Exception:
        pass
    try:
        print(msg, flush=True)
    except Exception:
        pass


def find_pythonw() -> str:
    """探测可用的 pythonw.exe（优先项目虚拟环境，其次系统 PATH）"""
    candidates = [
        os.path.join(ROOT, ".venv", "Scripts", "pythonw.exe"),
        os.path.join(ROOT, "pythonw.exe"),
        getattr(sys, "executable", ""),
    ]
    for c in candidates:
        if c and c.lower().endswith((".exe",)) and os.path.isfile(c):
            return c
    # sys.executable 可能是 python.exe，换成同目录 pythonw.exe
    exe = getattr(sys, "executable", "")
    if exe:
        alt = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(alt):
            return alt
    # PATH 兜底
    found = shutil.which("pythonw")
    if found:
        return found
    return "pythonw"  # 最后兜底：让系统解析


def _run_key_exists() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def install() -> bool:
    """写入开机自启注册表项（幂等）"""
    import winreg
    pyw = find_pythonw()
    script = os.path.abspath(__file__)
    cmd = f'"{pyw}" "{script}" --launch'
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
        log(f"[install] ✅ 开机自启已配置: {cmd}")
        return True
    except Exception as e:
        log(f"[install] ❌ 配置失败: {e}")
        return False


def uninstall() -> bool:
    """删除开机自启注册表项"""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, APP_NAME)
        log("[uninstall] ✅ 已取消开机自启")
        return True
    except FileNotFoundError:
        log("[uninstall] ⚠️ 未配置开机自启")
        return False
    except Exception as e:
        log(f"[uninstall] ❌ 取消失败: {e}")
        return False


def status() -> dict:
    """查看自启状态 + 端口状态"""
    info = {"autostart": _run_key_exists(), "port_open": port_open(DEFAULT_PORT)}
    log(f"[status] autostart={info['autostart']} port9900_open={info['port_open']}")
    return info


def port_open(port: int, timeout: float = 1.0) -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def launch() -> int:
    """启动 9900 WEB 服务（后台 pythonw + 日志文件，幂等：端口已开直接退出）"""
    if port_open(DEFAULT_PORT):
        log(f"[launch] ✅ 9900 服务已在运行，跳过启动")
        return 0

    pyw = find_pythonw()
    if not os.path.isfile(MAIN_PY):
        log(f"[launch] ❌ main.py 不存在: {MAIN_PY}")
        return 1

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        logf = open(SERVICE_LOG, "a", encoding="utf-8", buffering=1)
    except Exception as e:
        logf = None
        log(f"[launch] ⚠️ 无法打开日志文件: {e}")

    try:
        p = subprocess.Popen(
            [pyw, MAIN_PY, "--web", "--host", "0.0.0.0", "--port", str(DEFAULT_PORT)],
            cwd=ROOT,
            stdout=logf,
            stderr=logf,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        log(f"[launch] 🚀 已启动 WEB 服务 (PID={p.pid}, pyw={pyw})")
    except Exception as e:
        log(f"[launch] ❌ 启动失败: {e}")
        return 1

    # 轮询等待就绪（最多 30 秒）
    for i in range(30):
        time.sleep(1)
        if port_open(DEFAULT_PORT):
            log(f"[launch] ✅ 9900 就绪（{i + 1}s）→ http://127.0.0.1:9900/")
            return 0
    log(f"[launch] ⚠️ 30s 内未就绪，请查看日志: {SERVICE_LOG}")
    return 1


def main(argv: list = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法: web_autostart.py --install|--uninstall|--status|--launch")
        return 2
    action = argv[0]
    if action == "--install":
        return 0 if install() else 1
    if action == "--uninstall":
        return 0 if uninstall() else 1
    if action == "--status":
        status()
        return 0
    if action == "--launch":
        return launch()
    print(f"未知参数: {action}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
