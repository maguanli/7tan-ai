# -*- coding: utf-8 -*-
"""一次性原子重启 9900 WEB 服务：杀旧进程 -> 启动新进程 -> 验证健康
用系统 Python312 的 pythonw（与原服务一致，依赖齐全）
"""
import subprocess, time, os, sys, urllib.request, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 9900
PYW = r"C:\Program Files\Python312\pythonw.exe"
LOG = os.path.join(ROOT, "logs", "web_9900.log")

def log(msg):
    try:
        with open(os.path.join(ROOT, "logs", "web_autostart.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    except Exception:
        pass
    print(msg, flush=True)

def http_ok():
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2)
        return r.status == 200
    except Exception:
        return False

def port_pids():
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=10).stdout or ""
    pids = set()
    for line in out.splitlines():
        if f":{PORT}" in line and "LISTENING" in line:
            parts = line.split()
            if parts and parts[-1].isdigit():
                pids.add(parts[-1])
    return pids

# 0. 清理临时诊断脚本
for f in glob.glob(os.path.join(ROOT, "tmp_proc.py")):
    try: os.remove(f)
    except Exception: pass

# 1. 杀掉占用 9900 的所有进程
pids = port_pids()
log(f"[restart] 占用 9900 的 PID: {pids}")
for pid in pids:
    r = subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, text=True, timeout=10)
    log(f"[restart] kill {pid} -> rc={r.returncode} {r.stdout.strip()[:80]}")

# 2. 等待端口释放
for i in range(15):
    if not port_pids():
        break
    time.sleep(1)
log(f"[restart] 端口释放完成，等待 2s...")
time.sleep(2)

# 3. 启动新服务（与原服务一致：系统 Python312 pythonw + main.py --web）
os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
logf = open(LOG, "a", encoding="utf-8", buffering=1)
try:
    p = subprocess.Popen(
        [PYW, os.path.join(ROOT, "main.py"), "--web", "--host", "0.0.0.0", "--port", str(PORT)],
        cwd=ROOT, stdout=logf, stderr=logf,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )
    log(f"[restart] 已启动新服务 PID={p.pid}")
except Exception as e:
    log(f"[restart] 启动失败: {e}")
    sys.exit(1)

# 4. 轮询健康（最多 40s）
for i in range(40):
    time.sleep(1)
    if http_ok():
        log(f"[restart] HEALTH OK after {i+1}s, new PID={p.pid}")
        break
else:
    log("[restart] FAIL: 40s 内服务未就绪，请查 logs/web_9900.log")
    sys.exit(1)

log("[restart] DONE")
