# -*- coding: utf-8 -*-
import urllib.request, json, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 1) 端口探测
try:
    r = urllib.request.urlopen("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=4)
    data = json.loads(r.read())
    print("READY MODELS:", [m["model_name"] for m in data])
except Exception as e:
    print("NOT READY:", e)

# 2) 日志尾部
log = r"G:\AI_Video\stable-diffusion-webui\sd_cpu_log.txt"
if os.path.exists(log):
    sz = os.path.getsize(log)
    print("log size:", sz)
    with open(log, "rb") as f:
        f.seek(max(0, sz - 6000))
        tail = f.read().decode("utf-8", errors="replace")
    print("=== log tail ===")
    print(tail[-4000:])
else:
    print("log NOT FOUND")
