# -*- coding: utf-8 -*-
import subprocess, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
# python 进程
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
print("=== python procs ===")
print(r.stdout)

# pip 进程
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq pip.exe", "/FO", "CSV"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
print("=== pip procs ===")
print(r.stdout)

# 检查关键包是否已装
venv_py = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe"
code = "import importlib; mods=['git','blendmodes','diskcache','jsonmerge','piexif','psutil','kornia','skimage','spandrel','facexlib','protobuf','more_itertools','cleanfid','tomesd','torchdiffeq','torchsde'];[print(m, 'OK' if importlib.util.find_spec(m) else 'MISSING') for m in mods]"
r = subprocess.run([venv_py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("=== module check ===")
print(r.stdout)
print(r.stderr[-800:] if r.stderr else "")
