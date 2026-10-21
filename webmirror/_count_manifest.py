# -*- coding: utf-8 -*-
import os, json, collections, hashlib, re

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
MAN  = os.path.join(TASK, "_mirror_manifest.ndjson")
MANJ = os.path.join(TASK, "_mirror_manifest.json")
QUE  = os.path.join(TASK, "_mirror_queue.ndjson")

def count_lines(p):
    n = 0
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for _ in f:
            n += 1
    return n

print("manifest.ndjson 行数:", count_lines(MAN))
print("queue.ndjson 行数   :", count_lines(QUE))

# 解析 manifest.ndjson，收集每条的 url 和本地路径
urls = []
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
        u = o.get("url") or o.get("u") or ""
        urls.append(u)

print("manifest 可解析条数:", len(recs))
print("样例一条:", json.dumps(recs[0], ensure_ascii=False)[:300] if recs else "NA")

# URL 去重
uniq = set(urls)
print("URL 唯一数:", len(uniq), " 重复条数:", len(urls) - len(uniq))

# 看 manifest 里记录的字段名
keys = collections.Counter()
for o in recs[:5000]:
    for k in o.keys():
        keys[k] += 1
print("字段分布(前5000条):", dict(keys))
