# -*- coding: utf-8 -*-
import io, sys, os, shutil, zipfile, urllib.request, tempfile, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai"

# 查默认分支
try:
    req = urllib.request.Request("https://api.github.com/repos/Stability-AI/stablediffusion",
                                 headers={"User-Agent": "Mozilla/5.0"})
    info = json.loads(urllib.request.urlopen(req, timeout=30).read())
    branch = info.get("default_branch", "main")
    print("default branch:", branch)
    print("archived:", info.get("archived"), "| full_name:", info.get("full_name"))
except Exception as e:
    print("api failed:", e)
    branch = "main"

if os.path.isdir(repo):
    shutil.rmtree(repo, ignore_errors=True)
os.makedirs(repo, exist_ok=True)

url = f"https://codeload.github.com/Stability-AI/stablediffusion/zip/refs/heads/{branch}"
zip_path = os.path.join(tempfile.gettempdir(), "sd_stability.zip")
print("downloading:", url, flush=True)
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
    inner = os.path.join(repo, names[0].split("/")[0])
    if os.path.isdir(inner):
        for item in os.listdir(inner):
            shutil.move(os.path.join(inner, item), os.path.join(repo, item))
        shutil.rmtree(inner, ignore_errors=True)

p = os.path.join(repo, "ldm", "models", "diffusion", "ddpm.py")
print("ddpm.py exists:", os.path.exists(p))
print("top items:", os.listdir(repo)[:30])
