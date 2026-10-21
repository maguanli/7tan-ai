# -*- coding: utf-8 -*-
import os, json, collections

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
MAN  = os.path.join(TASK, "_mirror_manifest.ndjson")

paths = []
sizes = {}
with open(MAN, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        p = o.get("path", "")
        paths.append(p)
        sizes[p] = o.get("size", 0)

print("manifest 记录(pct)      :", len(paths))
print("path 唯一(区分大小写)   :", len(set(paths)))

low = [p.lower() for p in paths]
print("path 唯一(忽略大小写)   :", len(set(low)))
print("=> 大小写撞车损失页数   :", len(paths) - len(set(low)))

# 撞车例子
groups = collections.defaultdict(list)
for p in paths:
    groups[p.lower()].append(p)
coll = [(k, v) for k, v in groups.items() if len(v) > 1]
coll.sort(key=lambda x: -len(x[1]))
print("\n大小写撞车组数:", len(coll))
print("撞车最多的 15 组:")
for k, v in coll[:15]:
    print("   ", k)
    for p in v:
        print("        ", p, sizes.get(p))
