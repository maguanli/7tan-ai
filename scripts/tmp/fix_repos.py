# -*- coding: utf-8 -*-
import subprocess, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

repos = [
    r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai",
    r"G:\AI_Video\stable-diffusion-webui\repositories\k-diffusion",
]
for repo in repos:
    print("=" * 20, repo)
    r = subprocess.run(["git", "remote", "-v"], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    print("remote:", r.stdout.strip() or r.stderr.strip())
    r = subprocess.run(["git", "fetch", "origin"], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    print("fetch rc:", r.returncode, r.stderr[-800:] if r.stderr else "")
    r = subprocess.run(["git", "checkout", "-f", "origin/master"], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    print("checkout rc:", r.returncode, r.stderr[-500:] if r.stderr else "")
    # 验证关键文件
    if repo.endswith("stable-diffusion-stability-ai"):
        p = os.path.join(repo, "ldm", "models", "diffusion", "ddpm.py")
        print("ddpm.py exists:", os.path.exists(p))
    else:
        p = os.path.join(repo, "k_diffusion", "sampling.py")
        print("k_diffusion/sampling.py exists:", os.path.exists(p))
