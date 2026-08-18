# -*- coding: utf-8 -*-
"""
7Tan Web 服务开机自启管理器（产品级 · 适配绿色版免安装）

用法:
    python tools/web_autostart.py --install      # 配置开机自启（幂等 + 路径自愈）
    python tools/web_autostart.py --uninstall    # 取消开机自启
    python tools/web_autostart.py --status       # 查看自启状态 + 9900 端口状态
    python tools/web_autostart.py --launch       # 启动 9900 服务（端口已开则直接退出）

原理:
    - 写注册表 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
      （用户级自启，无需管理员权限、无需安装，绿色版解压即用）
    - 绿色版（ZIP 内 7tan-editor/7tan-editor.exe）：自启条目与启动均直接用
      7tan-editor.exe --web（exe 自带 Python 运行时，零依赖，无需安装 Node.js/Python）
    - 开发版（源码目录 + .venv）：pythonw 无窗口启动 main.py --web
    - 与桌面版单实例保护兼容（main.py 对 web 模式放行，可共存）

绿色版适配（免安装软件的独有坑）:
    用户可能移动/重命名软件目录，注册表里存的是绝对路径，目录变更后旧条目失效。
    因此 install() 实现「路径自愈」：
      - 已配置且路径与当前一致 → 跳过（幂等）
      - 已配置但路径与当前不一致 → 自动更新为新路径（目录变更自愈）
    「Windows-启动网页版服务.bat」每次双击都用 %~dp0 动态路径重新执行 install，
    WEB 服务每次启动（server.py）也会静默校准一次 → 移动目录后无需任何手动操作。
"""
import os
import sys
import time
import socket
import shutil
import subprocess

# 控制台输出容错：编码跟随系统代码页，无法编码的字符(emoji等)替换为?，
# 防止 GBK(936) 控制台下 print 中文/emoji 时抛 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

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


def find_main_exe() -> str:
    """绿色版主程序 7tan-editor.exe（exe 自带 Python 运行时，零依赖启动 WEB 服务）"""
    return os.path.join(ROOT, "7tan-editor.exe")


def is_exe_mode() -> bool:
    """是否绿色版（exe 模式）：exe 存在即优先使用，无需外部 Python 环境"""
    return os.path.isfile(find_main_exe())


def build_cmd() -> str:
    """构造注册表自启命令（幂等比较用；随当前运行形态动态生成，天然路径自愈）"""
    if is_exe_mode():
        exe = find_main_exe()
        return f'"{exe}" --web --host 0.0.0.0 --port {DEFAULT_PORT}'
    pyw = find_pythonw()
    script = os.path.abspath(__file__)
    return f'"{pyw}" "{script}" --launch'


def _read_reg() -> str | None:
    """读取当前自启注册表值；不存在/异常返回 None"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            return winreg.QueryValueEx(k, APP_NAME)[0]
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _run_key_exists() -> bool:
    return _read_reg() is not None


def install_protocol(silent: bool = False) -> bool:
    # 注册 7tan:// URL 协议 -> 触发本地启动脚本（服务死亡时也能一键拉起）。
    # 协议 handler 固定指向项目根目录的「启动网页版服务(Windows).bat」，
    # 该 bat 内部用 %~dp0 动态定位且幂等。绿色版移动目录后，由 install()
    # 每次启动路径自愈时顺带重新注册，保证协议始终指向正确路径。
    if os.name != "nt":
        return False
    import winreg
    bat = os.path.join(ROOT, "启动网页版服务(Windows).bat")
    proto_key = "Software" + "\\" + "Classes" + "\\" + "7tan"
    cmd_key = proto_key + "\\" + "shell" + "\\" + "open" + "\\" + "command"
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, proto_key) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "URL:7Tan Protocol")
            winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_key) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, '"' + bat + '" "%1"')
        if not silent:
            log("[protocol] 已注册 7tan:// 协议 -> " + bat)
        return True
    except Exception as e:
        if not silent:
            log("[protocol] 协议注册失败: " + str(e))
        return False


def install(silent: bool = False, force: bool = False) -> bool:
    """写入开机自启注册表项（幂等 + 绿色版路径自愈）。

    绿色版（免安装、解压即用）用户可能移动/重命名软件目录，
    注册表中存的是绝对路径，目录变更后旧条目会失效。因此：
    - 已配置且路径与当前一致 → 跳过（幂等）
    - 已配置但路径与当前不一致 → 自动更新为新路径（目录变更自愈）
    - 未配置 → 新建
    """
    import winreg
    # 顺带注册 7tan:// 协议（幂等），保证服务死亡时前端可一键拉起
    install_protocol(silent=silent)
    cmd = build_cmd()

    old = _read_reg()
    if not force and old == cmd:
        if not silent:
            log("[install] ✅ 开机自启已配置且路径正确，跳过")
        return True
    if old and old != cmd:
        log("[install] 🔄 检测到软件目录变更，自动更新自启路径")
        log(f"          旧: {old}")
        log(f"          新: {cmd}")
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
        if not silent:
            mode = "exe(绿色版)" if is_exe_mode() else "pythonw(开发版)"
            log(f"[install] ✅ 开机自启已配置 [{mode}]: {cmd}")
        return True
    except Exception as e:
        if not silent:
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


def http_ok(port: int = DEFAULT_PORT, timeout: float = 2.0) -> bool:
    """HTTP 健康检查：端口能连且 /api/health 有响应才算健康。
    解决「端口被假活进程占用（TCP 通但 HTTP 无响应）导致重启被跳过」的问题。"""
    try:
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def kill_port_owner(port: int) -> bool:
    """只杀掉占用指定端口的进程（比 taskkill /IM pythonw.exe 安全，不误伤其他 pythonw）。"""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True, timeout=10, text=True,
        ).stdout or ""
        pids = set()
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts and parts[-1].isdigit():
                    pids.add(parts[-1])
        killed = False
        for pid in pids:
            r = subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, timeout=10, text=True)
            if r.returncode == 0:
                log(f"[launch] 🔪 已强制结束占用 {port} 的进程 PID={pid}")
                killed = True
        return killed
    except Exception as e:
        log(f"[launch] ⚠️ 杀端口占用进程失败: {e}")
        return False


def launch() -> int:
    """启动 9900 WEB 服务（幂等：端口已开直接退出）。

    绿色版：直接启动 7tan-editor.exe --web（exe 自带 Python，零依赖）
    开发版：pythonw 无窗口启动 main.py --web，日志写入 logs/web_9900.log
    """
    if port_open(DEFAULT_PORT):
        if http_ok():
            log("[launch] ✅ 9900 服务已在运行且健康，跳过启动")
            return 0
        log("[launch] ⚠️ 端口被占用但 HTTP 无响应（疑似假活），强制重启…")
        kill_port_owner(DEFAULT_PORT)
        time.sleep(2)

    if is_exe_mode():
        exe = find_main_exe()
        try:
            p = subprocess.Popen(
                [exe, "--web", "--host", "0.0.0.0", "--port", str(DEFAULT_PORT)],
                cwd=ROOT,
            )
            log(f"[launch] 🚀 已启动 WEB 服务 (exe 绿色版, PID={p.pid}, exe={exe})")
        except Exception as e:
            log(f"[launch] ❌ 启动失败: {e}")
            return 1
    else:
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
