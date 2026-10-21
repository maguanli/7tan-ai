# -*- coding: utf-8 -*-
import os, json, collections

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
QUE  = os.path.join(TASK, "_mirror_queue.ndjson")

urls = []
with open(QUE, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            # 可能是纯 URL 行
            urls.append(line)
            continue
        u = o.get("url") or o.get("u") or ""
        urls.append(u)

def norm(u):
    # 去协议、去末尾斜杠、小写
    s = u.strip()
    for pre in ("https://", "http://"):
        if s.startswith(pre):
            s = s[len(pre):]
    s = s.rstrip("/").lower()
    return s

print("queue 总行数            :", len(urls))
print("队列 URL 唯一           :", len(set(urls)))
n = [norm(u) for u in urls]
print("队列 URL 唯一(忽略大小写):", len(set(n)))
print("=> 大小写重复膨胀        :", len(set(urls)) - len(set(n)))

# 只看你边网域名
dom = [u for u in urls if "293.net" in u]
nd  = [norm(u) for u in dom]
print("\n其中 293.net 相关:")
print("   行数:", len(dom), " 唯一:", len(set(dom)), " 忽略大小写唯一:", len(set(nd)))

# 抽样看判重后还剩多少真正不同
uniq_norm = set(n)
print("\n判重后真正不同 URL 总数:", len(uniq_norm))

# 展示一组例子
g = collections.defaultdict(list)
for u in urls:
    g[norm(u)].append(u)
coll = sorted([(k,v) for k,v in g.items() if len(v)>1], key=lambda x:-len(x[1]))
print("\n忽略大小写后仍有重复的组数:", len(coll))
for k, v in coll[:5]:
    print("  ", k, "→", len(v), "个")
    for u in v[:8]:
        print("       ", u)
