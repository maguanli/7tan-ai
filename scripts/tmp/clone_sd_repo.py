# -*- coding: utf-8 -*-
import subprocess, io, sys, os, shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai"

if os.path.isdir(repo):
    shutil.rmtree(repo, ignore_errors=True)
    print("removed old dir")

urls = [
    "https://github.com/Stability-AI/stablediffusion",
    "https://ghfast.top/https://github.com/Stability-AI/stablediffusion",
    "https://ghproxy.net/https://github.com/Stability-AI/stablediffusion",
]
ok = False
for url in urls:
    print("try clone:", url, flush=True)
    r = subprocess.run(["git", "clone", "--depth", "1", url, repo],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    print("rc:", r.returncode)
    if r.returncode == 0:
        ok = True
        break
    print(r.stderr[-600:] if r.stderr else r.stdout[-600:])

p = os.path.join(repo, "ldm", "models", "diffusion", "ddpm.py")
print("ddpm.py exists:", os.path.exists(p))
