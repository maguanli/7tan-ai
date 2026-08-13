# -*- coding: utf-8 -*-
import hashlib, os

WL = "77938293701be1e9087d39c9b48d94d42a25361282bad5036d73b17476b38eb2"

for label, p in [
    ("git_original", r"git_original_tools.py"),
    ("current", r"data/plugins/novel_writer/tools.py"),
]:
    if os.path.exists(p):
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        print(f"{label}: {h} size={os.path.getsize(p)} MATCH_WL={h == WL}")
    else:
        print(f"{label}: NOT FOUND")
