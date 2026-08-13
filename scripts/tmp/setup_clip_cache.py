# -*- coding: utf-8 -*-
import io, sys, os, urllib.request, hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 用自定义 HF_HOME（放 webui 目录下，可控）
HF_HOME = r"G:\AI_Video\stable-diffusion-webui\models\hf_cache"
snap = "a1b2c3d4e5f6"  # 任意 hash
repo_dir = os.path.join(HF_HOME, "hub", "models--openai--clip-vit-large-patch14")
snap_dir = os.path.join(repo_dir, "snapshots", snap)
os.makedirs(snap_dir, exist_ok=True)
os.makedirs(os.path.join(repo_dir, "refs"), exist_ok=True)

files = [
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "tokenizer.json",
    "config.json",
    "preprocessor_config.json",
]
base = "https://hf-mirror.com/openai/clip-vit-large-patch14/resolve/main/"
ok = 0
for f in files:
    url = base + f
    dst = os.path.join(snap_dir, f)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=60).read()
        with open(dst, "wb") as fh:
            fh.write(data)
        print("OK:", f, len(data))
        ok += 1
    except Exception as e:
        print("FAIL:", f, e)

# refs/main
with open(os.path.join(repo_dir, "refs", "main"), "w") as fh:
    fh.write(snap)
print("done, files:", ok, "/", len(files))
