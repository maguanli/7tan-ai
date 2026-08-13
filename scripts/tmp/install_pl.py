# -*- coding: utf-8 -*-
import subprocess, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
pip = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\pip.exe"
print("pip exists:", os.path.exists(pip))
if not os.path.exists(pip):
    py = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe"
    print("venv python exists:", os.path.exists(py))
    sys.exit(1)

r = subprocess.run([pip, "install", "pytorch_lightning", "-q"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
print("exit:", r.returncode)
print(r.stdout[-1500:] if r.stdout else "")
print(r.stderr[-1500:] if r.stderr else "")
