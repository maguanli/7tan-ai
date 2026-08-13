# -*- coding: utf-8 -*-
import time, urllib.request, json, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logf_path = r"G:\AI_Video\stable-diffusion-webui\sd_direct_log.txt"

def check():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=4)
        data = json.loads(r.read())
        return [m["model_name"] for m in data]
    except Exception:
        return None

last_size = 0
deadline = time.time() + 560
while time.time() < deadline:
    m = check()
    if m:
        print("READY! MODELS:", m)
        sys.exit(0)
    # 显示日志增量
    if os.path.exists(logf_path):
        sz = os.path.getsize(logf_path)
        if sz != last_size:
            last_size = sz
            with open(logf_path, "rb") as f:
                f.seek(max(0, sz - 3000))
                print("--- log grew:", sz, "---")
                print(f.read().decode("utf-8", errors="replace")[-2500:], flush=True)
    time.sleep(20)

print("STILL NOT READY after 560s")
sys.exit(1)
