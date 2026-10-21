# -*- coding: utf-8 -*-
import os, json, collections

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
MAN  = os.path.join(TASK, "_mirror_manifest.ndjson")

path_to_urls = collections.defaultdict(list)
recs = []
with open(MAN, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        recs.append(o)
        path_to_urls[o.get("path", "")].append(o.get("url", ""))

print("manifest 记录数:", len(recs))
print("不同 path 数  :", len(path_to_urls))
print("=> path 碰撞(多个URL写同一文件) 造成的损失:", len(recs) - len(path_to_urls))

# 碰撞最严重的例子
coll = [(p, us) for p, us in path_to_urls.items() if len(us) > 1]
coll.sort(key=lambda x: -len(x[1]))
print("\n碰撞组数:", len(coll), " 涉及记录数:", sum(len(us) for _, us in coll))
print("\n碰撞最多的 10 组:")
for p, us in coll[:10]:
    print("  路径:", p)
    for u in us[:6]:
        print("      <-", u)

# 现在检查磁盘：manifest 里的 path 是否真的存在
missing = [p for p in path_to_urls if not os.path.exists(os.path.join(TASK, p))]
print("\nmanifest 中 path 不存在于磁盘的:", len(missing))
for p in missing[:15]:
    print("   MISSING:", p, "<-", path_to_urls[p][:2])
