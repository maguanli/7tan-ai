# -*- coding: utf-8 -*-
import io, sys, os, urllib.request, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
try:
    req = urllib.request.Request("https://hf-mirror.com/api/models/openai/clip-vit-large-patch14",
                                 headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    for s in data.get("siblings", []):
        print(s.get("rfilename"))
except Exception as e:
    print("FAIL:", e)
