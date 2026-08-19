# -*- coding: utf-8 -*-
import io, sys, os, shutil, zipfile, urllib.request, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories\generative-models"

candidates = [
    ("Stability-AI/generative-models", "main"),
    ("Stability-AI/generative-models", "master"),
]

ok = False
for name, branch in candidates:
    print(f"--- try {name}@{branch} ---", flush=True)
    if os.path.isdir(repo):
        shutil.rmtree(repo, ignore_errors=True)
    os.makedirs(repo, exist_ok=True)
    url = f"https://codeload.github.com/{name}/zip/refs/heads/{branch}"
    zip_path = os.path.join(tempfile.gettempdir(), "gm.zip")
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
    p = os.path.join(repo, "sgm", "__init__.py")
    if os.path.exists(p):
        print("SUCCESS! sgm exists")
        print("top items:", os.listdir(repo)[:20])
        ok = True
        break
    else:
        print("sgm NOT found, items:", os.listdir(repo)[:20])

if not ok:
    print("ALL FAILED")
    sys.exit(1)
