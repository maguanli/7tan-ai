# -*- coding: utf-8 -*-
import io, sys, os, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
midas_dir = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai\ldm\modules\midas"
os.makedirs(midas_dir, exist_ok=True)

files = ["midas.py", "api.py", "__init__.py"]
forks = [
    "AbdullahAlfaraj/stable-diffusion-stability-ai/main",
    "bm128/stable-diffusion-v1-5/main",
    "sd-webui/stable-diffusion-webui/main",
    "albarji/stable-diffusion-stability-ai/main",
]

ok_count = 0
for fname in files:
    got = False
    for fork in forks:
        url = f"https://raw.githubusercontent.com/{fork}/ldm/modules/midas/{fname}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30).read()
            with open(os.path.join(midas_dir, fname), "wb") as f:
                f.write(data)
            print("OK:", fname, "from", fork, len(data), "bytes")
            got = True
            ok_count += 1
            break
        except Exception as e:
            print("fail:", fname, fork, e)
    if not got:
        print("MISSING:", fname)

print("done, ok:", ok_count, "/", len(files))
