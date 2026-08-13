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
            f.seek(max(0, os.path.getsize(logf_path) - 6000))
            return f.read().decode("utf-8", errors="replace")[-5000:]
    return ""

# 常见可能缺的包，一次装齐（轻量）
common = ["gradio", "einops", "omegaconf", "safetensors", "accelerate", "transformers", "inflection", "Pillow"]
print("pre-install:", common)
r = subprocess.run([venv_pip, "install", "-q"] + common,
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
print("pre-install rc:", r.returncode)

for attempt in range(6):
    print(f"--- attempt {attempt+1}: start ---")
    logf = open(logf_path, "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen([venv_py, "launch.py",
                          "--api", "--nowebui", "--skip-install", "--skip-python-version-check",
                          "--skip-torch-cuda-test", "--no-half", "--use-cpu", "all",
                          "--precision", "full", "--skip-prepare-environment"],
                         cwd=webui, stdout=logf, stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    print("pid:", p.pid)
    # 等待 90 秒看是否 ready 或 crash
    deadline = time.time() + 90
    ready = False
    while time.time() < deadline:
        m = check()
        if m:
            print("READY! MODELS:", m)
            sys.exit(0)
        time.sleep(10)
    logf.close()
    # 未 ready，检查日志找缺的模块
    log = tail_log()
    m = re.search(r"ModuleNotFoundError: No module named '([^']+)'", log)
    if m:
        mod = m.group(1)
        print("missing module:", mod)
        # 处理 gradio 相关常见依赖名
        rr = subprocess.run([venv_pip, "install", "-q", mod],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        print("install", mod, "rc:", rr.returncode)
        continue
    print("=== log tail ===")
    print(log[-3000:])
    break

print("FAILED after attempts")
sys.exit(1)
