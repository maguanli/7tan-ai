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
        p = o.get("path", "")
        groups[p.lower()].append((o.get("url", ""), o.get("size", 0)))

coll = [(k, v) for k, v in groups.items() if len(v) > 1]
same_size = 0
diff_size = 0
lost = 0
for k, v in coll:
    sizes = set(s for _, s in v)
    if len(sizes) == 1:
        same_size += 1
    else:
        diff_size += 1
    lost += len(v) - 1

print("撞车组总数        :", len(coll))
print("  组内大小完全相同:", same_size)
print("  组内大小有不同  :", diff_size)
print("被覆盖掉的记录条数:", lost)
print("现存文件数        :", len(groups))

# 看几组大小不同的，确认不是同一份内容
print("\n大小不同的例子(说明服务器对不同大小写返回的内容不一样):")
shown = 0
for k, v in coll:
    if len(set(s for _, s in v)) > 1:
        print("  ", k)
        for u, s in v:
            print("        size=%-6d %s" % (s, u))
        shown += 1
        if shown >= 4:
            break
