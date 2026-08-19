# -*- coding: utf-8 -*-
import os, hashlib, json

WL = "77938293701be1e9087d39c9b48d94d42a25361282bad5036d73b17476b38eb2"

# 1) 找 exe 和 _internal
print("=== exe / _internal 搜索 ===")
for root in [r"D:\7tan"]:
    for dp, dn, fn in os.walk(root):
        depth = dp[len(root):].count(os.sep)
        if depth > 3:
            dn[:] = []
            continue
        for f in fn:
            if f.endswith(".exe") or "internal" in dp.lower():
                pass
        if "_internal" in dp:
            print("DIR:", dp)
        for f in fn:
            if f.lower().endswith(".exe") and "7tan" in f.lower():
                print("EXE:", os.path.join(dp, f))

# 2) 签名工具链
print("=== 签名工具 ===")
for cand in [
    r"tools\gen_plugin_hashes.py",
    r"tools\gen_plugin_guard.py",
    r"tools\security_src\gen_plugin_hashes.py",
]:
    print(cand, "->", os.path.exists(cand))

# 3) 搜索 novel_writer 目录副本（含 _internal）
print("=== novel_writer 副本 ===")
for root in [r"D:\7tan"]:
    for dp, dn, fn in os.walk(root):
        if dp.count(os.sep) - root.count(os.sep) > 4:
            dn[:] = []
            continue
        if dp.endswith("novel_writer") and "tools.py" in fn:
            fp = os.path.join(dp, "tools.py")
            h = hashlib.sha256(open(fp, "rb").read()).hexdigest()
            print("COPY:", fp, "MATCH_WL:", h == WL)
