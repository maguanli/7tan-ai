# -*- coding: utf-8 -*-
import subprocess, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
venv_pip = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\pip.exe"
venv_py = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe"

r = subprocess.run([venv_pip, "install", "-q", "pydantic<2"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
print("pydantic downgrade rc:", r.returncode)
print((r.stdout or "")[-1200:])
print((r.stderr or "")[-1500:])

code = "import pydantic; print('pydantic', pydantic.VERSION)"
r2 = subprocess.run([venv_py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("verify:", r2.stdout, r2.stderr[-500:] if r2.stderr else "")
