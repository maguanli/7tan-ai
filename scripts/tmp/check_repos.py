# -*- coding: utf-8 -*-
import os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories"
print("exists:", os.path.isdir(repo))
if os.path.isdir(repo):
    for x in os.listdir(repo):
        full = os.path.join(repo, x)
        print(x, "(dir)" if os.path.isdir(full) else "(file)")
