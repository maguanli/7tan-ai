# -*- coding: utf-8 -*-
"""深挖 youbian 任务：stats / errors / 落盘体量 / 磁盘余量"""
import json, os, io, sys, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\7tan\7tanAI\webmirror\downloads"
D = os.path.join(ROOT, "20261011-063926-4ba5eb")

print("== stats ==")
m = json.load(open(os.path.join(D, "_mirror_manifest.json"), encoding="utf-8"))
print(json.dumps(m.get("stats", {}), ensure_ascii=False, indent=2))
print("\n== config ==")
print(json.dumps(m.get("config", {}), ensure_ascii=False, indent=2))
print("\n== errors (2) ==")
for e in m.get("errors", []):
    print("  ", json.dumps(e, ensure_ascii=False)[:300])

print("\n== files 前 3 条 ==")
for f in m.get("files", [])[:3]:
    print("  ", json.dumps(f, ensure_ascii=False)[:300])
print("== files 末 3 条 ==")
for f in m.get("files", [])[-3:]:
    print("  ", json.dumps(f, ensure_ascii=False)[:300])

# 落盘体量
total = 0; n = 0
for dp, dn, fn in os.walk(D):
    for x in fn:
        try: total += os.path.getsize(os.path.join(dp, x)); n += 1
        except: pass
print("\n== 落盘 ==\n文件数 %d | 合计 %.1f MB" % (n, total/1048576))

print("\n== 磁盘 ==")
for p in ("D:\\", "C:\\"):
    try:
        t, u, f = shutil.disk_usage(p)
        print("  %s 总 %.1f GB | 已用 %.1f GB | 剩余 %.1f GB" % (p, t/2**30, u/2**30, f/2**30))
    except Exception as e:
        print("  ", p, e)
