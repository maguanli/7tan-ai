# -*- coding: utf-8 -*-
import os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai"
print("exists:", os.path.isdir(repo))
if os.path.isdir(repo):
    print("items:", os.listdir(repo)[:50])
    for dp, dn, fn in os.walk(repo):
        depth = dp[len(repo):].count(os.sep)
        if depth <= 2:
            print("DIR:", dp[len(repo):] or "\\", "files:", len(fn))
