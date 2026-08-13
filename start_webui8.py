# -*- coding: utf-8 -*-
import subprocess, time, urllib.request, json, sys, io, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
webui = r"G:\AI_Video\stable-diffusion-webui"
venv_py = os.path.join(webui, "venv", "Scripts", "python.exe")
venv_pip = os.path.join(webui, "venv", "Scripts", "pip.exe")
logf_path = os.path.join(webui, "sd_direct_log.txt")

def check():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=4)
        data = json.loads(r.read())
        return [m["model_name"] for m in data]
    except Exception:
        return None

def tail_log():
    if os.path.exists(logf_path):
        with open(logf_path, "rb") as f:
            f.seek(max(0, os.path.getsize(logf_path) - 8000))
            return f.read().decode("utf-8", errors="replace")[-6000:]
    return ""

env = dict(os.environ)
env["HF_HOME"] = r"G:\AI_Video\stable-diffusion-webui\models\hf_cache"
env["HF_HUB_OFFLINE"] = "1"
env["TRANSFORMERS_OFFLINE"] = "1"
env["HF_ENDPOINT"] = "https://hf-mirror.com"

for attempt in range(4):
    print(f"--- attempt {attempt+1} ---", flush=True)
    logf = open(logf_path, "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen([venv_py, "launch.py",
                          "--api", "--nowebui", "--skip-install", "--skip-python-version-check",
                          "--skip-torch-cuda-test", "--no-half", "--use-cpu", "all",
                          "--precision", "full", "--skip-prepare-environment"],
                         cwd=webui, stdout=logf, stderr=subprocess.STDOUT, env=env,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    print("pid:", p.pid, flush=True)
    deadline = time.time() + 300
    while time.time() < deadline:
        m = check()
        if m:
            print("READY! MODELS:", m)
            sys.exit(0)
        time.sleep(10)
    logf.close()
    log = tail_log()
    m = re.search(r"ModuleNotFoundError: No module named '([^']+)'", log)
    if m:
        mod = m.group(1)
        print("missing module:", mod, flush=True)
        rr = subprocess.run([venv_pip, "install", "-q", mod],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        print("install", mod, "rc:", rr.returncode, flush=True)
        continue
    print("=== log tail ===")
    print(log[-4000:])
    break

print("FAILED")
sys.exit(1)
