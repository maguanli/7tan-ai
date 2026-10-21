# -*- coding: utf-8 -*-
import os, json, collections

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
MAN  = os.path.join(TASK, "_mirror_manifest.ndjson")

buckets = collections.Counter()
tiny = []
n = 0
with open(MAN, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        n += 1
        s = o.get("size", 0)
        if s < 200:      b = "A. <200B"
        elif s < 1000:   b = "B. 200-1KB"
        elif s < 4000:   b = "C. 1-4KB"
        elif s < 8000:   b = "D. 4-8KB"
        elif s < 20000:  b = "E. 8-20KB"
        else:            b = "F. >20KB"
        buckets[b] += 1
        if s < 1000 and len(tiny) < 8:
            tiny.append((s, o.get("url")))

print("manifest 记录数:", n)
print("\n页面大小分布:")
for b in sorted(buckets):
    print("   %-10s %8d  (%.2f%%)" % (b, buckets[b], buckets[b]*100.0/n))
print("\n小于 1KB 的例子(多半是跳转空壳):")
for s, u in tiny:
    print("   %-6d %s" % (s, u))
