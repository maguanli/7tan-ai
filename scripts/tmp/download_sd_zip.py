# -*- coding: utf-8 -*-
import subprocess, io, sys, os, shutil, zipfile, urllib.request, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai"

if os.path.isdir(repo):
    shutil.rmtree(repo, ignore_errors=True)
os.makedirs(repo, exist_ok=True)

url = "https://codeload.github.com/Stability-AI/stablediffusion/zip/refs/heads/main"
zip_path = os.path.join(tempfile.gettempdir(), "sd_stability.zip")
print("downloading...", url, flush=True)
try:
    urllib.request.urlretrieve(url, zip_path)
    print("downloaded, size:", os.path.getsize(zip_path))
except Exception as e:
    print("download failed:", e)
    sys.exit(1)

with zipfile.ZipFile(zip_path) as z:
    names = z.namelist()
    print("zip entries:", len(names), "first:", names[0])
    z.extractall(repo)
    # zip 内含一个顶层目录 stablediffusion-main/，把内容上移
    inner = os.path.join(repo, "stablediffusion-main")
    if os.path.isdir(inner):
        for item in os.listdir(inner):
            src = os.path.join(inner, item)
            dst = os.path.join(repo, item)
            if os.path.isdir(src):
                shutil.move(src, dst)
            else:
                shutil.move(src, dst)
        shutil.rmtree(inner, ignore_errors=True)

p = os.path.join(repo, "ldm", "models", "diffusion", "ddpm.py")
print("ddpm.py exists:", os.path.exists(p))
print("top items:", os.listdir(repo)[:30])
