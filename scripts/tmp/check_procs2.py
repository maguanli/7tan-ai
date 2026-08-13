# -*- coding: utf-8 -*-
import subprocess, io, sys, os, importlib.util as iu

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
venv_py = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe"
code = ("import importlib.util as iu;"
        "mods=['git','blendmodes','diskcache','jsonmerge','piexif','psutil','kornia','skimage','spandrel','facexlib','protobuf','more_itertools','cleanfid','tomesd','torchdiffeq','torchsde','PIL'];"
        "[print(m, 'OK' if iu.find_spec(m) else 'MISSING') for m in mods]")
r = subprocess.run([venv_py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("=== module check ===")
print(r.stdout)
print(r.stderr[-800:] if r.stderr else "")

# 端口
import urllib.request, json
try:
    rr = urllib.request.urlopen("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=5)
    print("READY:", json.loads(rr.read()))
except Exception as e:
    print("NOT READY:", e)
