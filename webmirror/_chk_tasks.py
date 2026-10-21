# -*- coding: utf-8 -*-
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

d = json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/tasks", timeout=15))
ts = d.get("tasks", [])
print("任务总数:", len(ts))

running = [t for t in ts if t.get("status") not in ("done", "failed", "stopped", "cancelled")]
print("非终态(可能仍在跑)的任务:", len(running))
for t in running:
    print("  ", t["id"], t.get("status"), t.get("start_url"))

print("\n=== youbian 相关任务 ===")
for t in ts:
    u = t.get("start_url", "")
    if "youbian" in u or "293.net" in u:
        cfg = t.get("config", {})
        st = t.get("stats", {})
        print(f"{t['id']}  {t.get('status'):8}  max_pages={cfg.get('max_pages')}  "
              f"pages_total={st.get('pages_total')}  pages_ok={st.get('pages_ok')}  "
              f"queue={st.get('queue_size')}")

print("\n=== 全部任务状态分布 ===")
from collections import Counter
print(Counter(t.get("status") for t in ts))
