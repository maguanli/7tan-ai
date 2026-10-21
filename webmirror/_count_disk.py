# -*- coding: utf-8 -*-
import os, json, collections

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
MAN  = os.path.join(TASK, "_mirror_manifest.ndjson")

groups = collections.defaultdict(list)
with open(MAN, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        groups[o.get("path","").lower()].append(o)

coll = [(k, v) for k, v in groups.items() if len(v) > 1]

stub = 0      # 磁盘上是空壳/跳转小文件
real = 0      # 磁盘上是真页面
missing = 0
small_files = []
for k, v in coll:
    fp = os.path.join(TASK, k)
    if not os.path.exists(fp):
        missing += 1
        continue
    sz = os.path.getsize(fp)
    if sz < 800:
        stub += 1
        if len(small_files) < 10:
            small_files.append((k, sz, [r.get("size") for r in v]))
    else:
        real += 1

print("撞车组总数            :", len(coll))
print("  磁盘上是小文件(<800B):", stub, "  <-- 真内容可能被覆盖")
print("  磁盘上是正常页面     :", real)
print("  文件不存在           :", missing)

print("\n被'小文件'占位的例子（看：磁盘大小 vs 当初各URL记录的大小）:")
for k, sz, sizes in small_files:
    print("  磁盘=%-5d  记录各URL=%-20s  %s" % (sz, sizes, k))
