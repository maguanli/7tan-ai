# -*- coding: utf-8 -*-
import os, hashlib

WL = "77938293701be1e9087d39c9b48d94d42a25361282bad5036d73b17476b38eb2"
print("=== dist/_internal 内置插件 ===")
base = r"D:\7tan\7tanAI\dist\7tan-editor"
print("dist exists:", os.path.isdir(base))
if os.path.isdir(base):
    print("dist items:", os.listdir(base)[:20])
    internal = os.path.join(base, "_internal")
    if os.path.isdir(internal):
        print("_internal items:", os.listdir(internal)[:30])
        pd = os.path.join(internal, "data", "plugins")
        if os.path.isdir(pd):
            print("_internal/data/plugins:", os.listdir(pd)[:50])
            for pid in os.listdir(pd):
                tp = os.path.join(pd, pid, "tools.py")
                if os.path.isfile(tp):
                    h = hashlib.sha256(open(tp, "rb").read()).hexdigest()
                    print("  bundled", pid, "MATCH_WL:", h == WL, h[:16])
        hf = os.path.join(pd, "hashes.json") if os.path.isdir(pd) else None
        # 内置白名单可能直接在 _internal/data/plugins/hashes.json
        cand = os.path.join(internal, "data", "plugins", "hashes.json")
        if os.path.exists(cand):
            import json
            d = json.load(open(cand, encoding="utf-8"))
            print("bundled hashes novel_writer:", d["plugins"].get("novel_writer"))
