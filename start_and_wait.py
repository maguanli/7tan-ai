# -*- coding: utf-8 -*-
import subprocess, time, urllib.request, json, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
bat = r"G:\AI_Video\stable-diffusion-webui\start_cpu.bat"

# 启动
p = subprocess.Popen(["cmd", "/c", bat], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
print("webui starting, pid:", p.pid)

def check():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=4)
        data = json.loads(r.read())
        return [m["model_name"] for m in data]
    except Exception:
        return None

deadline = time.time() + 540
while time.time() < deadline:
    m = check()
    if m:
        print("READY! MODELS:", m)
        sys.exit(0)
    time.sleep(20)
    print("...", int(deadline - time.time()), "s left", flush=True)

# 超时后显示日志尾部
log = r"G:\AI_Video\stable-diffusion-webui\sd_cpu_log.txt"
if os.path.exists(log):
    with open(log, "rb") as f:
        f.seek(max(0, os.path.getsize(log) - 4000))
        print("=== log tail ===")
        print(f.read().decode("utf-8", errors="replace")[-3000:])
print("TIMEOUT")
sys.exit(1)
