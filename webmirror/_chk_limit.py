# -*- coding: utf-8 -*-
"""查看镜像任务：页面上限 vs 实际抓取页数"""
import json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\7tan\7tanAI\webmirror\downloads"

# 1) 任务索引
idx = os.path.join(ROOT, "_tasks.json")
raw = open(idx, encoding="utf-8").read()
d = json.loads(raw)
tasks = d if isinstance(d, list) else d.get("tasks", list(d.values()) if isinstance(d, dict) else [])
print("== _tasks.json ==")
print("类型:", type(d).__name__, "| 任务数:", len(tasks))

def g(t, *keys, default=""):
    for k in keys:
        if isinstance(t, dict) and k in t and t[k] not in (None, ""):
            return t[k]
    return default

rows = []
for t in tasks:
    if not isinstance(t, dict):
        continue
    cfg = t.get("config") or t.get("cfg") or {}
    st  = t.get("stats") or {}
    url = g(t, "url", "start_url") or g(cfg, "start_url", "url")
    tid = g(t, "id", "task_id")
    mp  = g(cfg, "max_pages") or g(t, "max_pages", default="?")
    pages = g(st, "pages_total") or g(t, "pages_total", default="?")
    assets = g(st, "assets_total") or g(t, "assets_total", default="?")
    status = g(t, "status")
    rows.append((tid, url, mp, pages, assets, status))

rows.sort(key=lambda r: str(r[1]))
print("\n%-24s %-42s %8s %8s %8s %s" % ("任务ID", "起始网址", "上限", "页数", "资源", "状态"))
for r in rows:
    print("%-24s %-42s %8s %8s %8s %s" % (r[0][:24], str(r[1])[:42], r[2], r[3], r[4], r[5]))

# 2) 定位 youbian 任务，统计 manifest / state
print("\n== youbian 任务明细 ==")
for name in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, name)
    if not os.path.isdir(p):
        continue
    man = os.path.join(p, "_mirror_manifest.json")
    stf = os.path.join(p, "_mirror_state.json")
    if not os.path.exists(man):
        continue
    sz = os.path.getsize(man)
    if sz < 5_000_000:
        continue
    print("目录:", name, "| manifest", round(sz/1048576,1), "MB")
    try:
        m = json.load(open(man, encoding="utf-8"))
        print("  manifest keys:", list(m.keys())[:12])
        for k in ("max_pages", "pages_total", "pages_ok", "pages_failed", "assets_total",
                  "start_url", "url", "status", "finished", "complete", "stopped", "stop_reason"):
            if isinstance(m, dict) and k in m:
                print("   ", k, "=", m[k])
        if isinstance(m, dict):
            for k, v in m.items():
                if isinstance(v, list):
                    print("   list", k, "len =", len(v))
    except Exception as e:
        print("  读取 manifest 失败:", e)
    if os.path.exists(stf):
        print("  state:", round(os.path.getsize(stf)/1048576,1), "MB")
