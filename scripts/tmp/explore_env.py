# -*- coding: utf-8 -*-
import os, sys

print("CWD:", os.getcwd())
print("PYTHON:", sys.executable)
print()

# 1) 找 plugins 目录
for cand in ["plugins", "src/plugins", "."]:
    if os.path.isdir(cand):
        try:
            items = os.listdir(cand)
            print(f"[{cand}] exists, items({len(items)}):", items[:60])
        except Exception as e:
            print(f"[{cand}] listdir error:", e)
        break
else:
    print("[plugins] NOT FOUND in cwd")

print()
# 2) stable-diffusion-webui 目录
p = r"G:\AI_Video\stable-diffusion-webui"
if os.path.isdir(p):
    print("[webui] exists")
    print("  root:", os.listdir(p))
    sd = os.path.join(p, "models", "Stable-diffusion")
    if os.path.isdir(sd):
        print("  Stable-diffusion:", os.listdir(sd))
    ext = os.path.join(p, "extensions")
    if os.path.isdir(ext):
        print("  extensions:", os.listdir(ext))
else:
    print("[webui] NOT FOUND:", p)

print()
# 3) 是否有 GPU / torch
try:
    import torch
    print("torch:", torch.__version__, "cuda available:", torch.cuda.is_available())
except Exception as e:
    print("torch import error:", e)
