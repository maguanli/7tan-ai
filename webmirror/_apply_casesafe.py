# -*- coding: utf-8 -*-
import os, json, shutil

T = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
P = r"D:\7tan\7tanAI\webmirror\downloads\_tasks.json"
TID = "20261011-063926-4ba5eb"
CS = os.path.join(T, "_case_safe.json")

# 1) 流水账改名 ndjson -> tsv
old = os.path.join(T, "_mirror_queue.ndjson")
new = os.path.join(T, "_mirror_queue.tsv")
print("old exists:", os.path.isfile(old), "| new exists:", os.path.isfile(new))
if os.path.isfile(old) and not os.path.isfile(new):
    os.replace(old, new)
    print("RENAMED ->", new)
print("after: old?", os.path.isfile(old), "new?", os.path.isfile(new))

# 2) 任务配置：抬高 max_pages + 指定 case_safe_file
shutil.copy2(P, P + ".bak_20261015_casesafe")
d = json.load(open(P, encoding="utf-8"))
t = [x for x in d if x["id"] == TID][0]
old_mp = t["config"].get("max_pages")
t["config"]["max_pages"] = 2600000
t["config"]["case_safe_file"] = CS
json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("max_pages:", old_mp, "->", t["config"]["max_pages"])
print("case_safe_file:", t["config"]["case_safe_file"])
print("status:", t["status"])
