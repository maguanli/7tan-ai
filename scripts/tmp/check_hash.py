# -*- coding: utf-8 -*-
import hashlib, os, json

p = r"data/plugins/novel_writer/tools.py"
h = hashlib.sha256(open(p, "rb").read()).hexdigest()
print("current tools.py sha256:", h)
wl = json.load(open(r"data/plugins/hashes.json", encoding="utf-8"))
print("whitelist novel_writer :", wl["plugins"].get("novel_writer"))
print("MATCH:", h == wl["plugins"].get("novel_writer"))

# 找系统里的其他 novel_writer tools.py 副本
import sys
roots = [r"D:\7tan", r"G:\AI_Video", r"G:\AI_Tools"]
for root in roots:
    if not os.path.isdir(root):
        continue
    for dp, dn, fn in os.walk(root):
        if dp.count(os.sep) - root.count(os.sep) > 5:
            dn[:] = []
            continue
        if dp.endswith("novel_writer") and "tools.py" in fn:
            fp = os.path.join(dp, "tools.py")
            hh = hashlib.sha256(open(fp, "rb").read()).hexdigest()
            print("COPY:", fp, hh, "MATCH:", hh == wl["plugins"].get("novel_writer"))
