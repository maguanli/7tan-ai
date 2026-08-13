# -*- coding: utf-8 -*-
import io, sys, os, shutil, zipfile, urllib.request, tempfile, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai"

candidates = [
    ("runwayml/stable-diffusion", "main"),
    ("CompVis/stable-diffusion", "main"),
    ("runwayml/stable-diffusion", "master"),
    ("CompVis/stable-diffusion", "master"),
]

ok = False
for name, branch in candidates:
    print(f"--- try {name}@{branch} ---", flush=True)
    if os.path.isdir(repo):
        shutil.rmtree(repo, ignore_errors=True)
    os.makedirs(repo, exist_ok=True)
    url = f"https://codeload.github.com/{name}/zip/refs/heads/{branch}"
    zip_path = os.path.join(tempfile.gettempdir(), "sd_stability.zip")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("downloaded:", os.path.getsize(zip_path))
    except Exception as e:
        print("download failed:", e)
        continue
    try:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            z.extractall(repo)
            inner = os.path.join(repo, names[0].split("/")[0])
            if os.path.isdir(inner):
                for item in os.listdir(inner):
                    shutil.move(os.path.join(inner, item), os.path.join(repo, item))
                shutil.rmtree(inner, ignore_errors=True)
    except Exception as e:
        print("extract failed:", e)
        continue
    p = os.path.join(repo, "ldm", "models", "diffusion", "ddpm.py")
    if os.path.exists(p):
        print("SUCCESS! ddpm.py exists")
        print("top items:", os.listdir(repo)[:30])
        ok = True
        break
    else:
        print("ddpm.py NOT found, items:", os.listdir(repo)[:20])

if not ok:
    print("ALL FAILED")
    sys.exit(1)
