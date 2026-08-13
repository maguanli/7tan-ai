# -*- coding: utf-8 -*-
import os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
d = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai"
print("exists:", os.path.isdir(d))
if os.path.isdir(d):
    items = os.listdir(d)
    print("items:", items[:40])
    for sub in ["ldm", "scripts", "configs"]:
        print(sub, "->", os.path.isdir(os.path.join(d, sub)))
