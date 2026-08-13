# -*- coding: utf-8 -*-
import urllib.request, json, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
try:
    r = urllib.request.urlopen("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=5)
    data = json.loads(r.read())
    print("READY MODELS:", [m["model_name"] for m in data])
except Exception as e:
    print("NOT READY:", e)

log = r"G:\AI_Video\stable-diffusion-webui\sd_direct_log.txt"
if os.path.exists(log):
    sz = os.path.getsize(log)
    print("log size:", sz)
    with open(log, "rb") as f:
        f.seek(max(0, sz - 8000))
        print("=== log tail ===")
        print(f.read().decode("utf-8", errors="replace")[-6000:])
