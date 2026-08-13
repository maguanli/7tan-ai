# -*- coding: utf-8 -*-
import urllib.request, json, time, sys

def check():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=4)
        data = json.loads(r.read())
        return [m["model_name"] for m in data]
    except Exception as e:
        return None

for i in range(40):
    m = check()
    if m:
        print("READY after ~", (i+1)*15, "s")
        print("MODELS:", m)
        sys.exit(0)
    print("waiting", (i+1)*15, "s", flush=True)
    time.sleep(15)
print("TIMEOUT")
sys.exit(1)
