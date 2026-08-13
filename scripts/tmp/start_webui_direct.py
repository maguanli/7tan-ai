# -*- coding: utf-8 -*-
import subprocess, time, urllib.request, json, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
webui = r"G:\AI_Video\stable-diffusion-webui"
venv_py = os.path.join(webui, "venv", "Scripts", "python.exe")

# 检查可能干扰的 settings 文件
for f in ["webui.settings.bat"]:
    print(f, "exists:", os.path.exists(os.path.join(webui, f)))

args = [venv_py, "launch.py",
        "--api", "--nowebui", "--skip-install", "--skip-python-version-check",
        "--skip-torch-cuda-test", "--no-half", "--use-cpu", "all",
        "--precision", "full", "--skip-prepare-environment"]
logf = open(os.path.join(webui, "sd_direct_log.txt"), "w", encoding="utf-8", errors="replace")
p = subprocess.Popen(args, cwd=webui, stdout=logf, stderr=subprocess.STDOUT,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
print("direct webui started, pid:", p.pid)

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

logf.close()
log = os.path.join(webui, "sd_direct_log.txt")
if os.path.exists(log):
    with open(log, "rb") as f:
        f.seek(max(0, os.path.getsize(log) - 4000))
        print("=== direct log tail ===")
        print(f.read().decode("utf-8", errors="replace")[-3000:])
print("TIMEOUT")
sys.exit(1)
