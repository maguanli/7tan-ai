# -*- coding: utf-8 -*-
import sys, io, json, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API = "http://127.0.0.1:8000"

def post(path, payload):
    req = urllib.request.Request(API + path,
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    return json.load(urllib.request.urlopen(req, timeout=20))

def get(path):
    return json.load(urllib.request.urlopen(API + path, timeout=20))

print("=== 提交任务：max_pages=1000000, max_depth=0（只抓起始页）===")
try:
    r = post("/api/tasks", {
        "url": "http://youbian.293.net/",
        "max_depth": 0,
        "max_pages": 1000000,
        "concurrency": 4,
        "include_assets": False,
    })
    print("提交返回:", json.dumps(r, ensure_ascii=False))
    tid = (r.get("tasks") or [{}])[0].get("id") if isinstance(r.get("tasks"), list) else r.get("id")
    if not tid:
        tid = r.get("id")
    print("任务ID:", tid)
except Exception as e:
    print("提交失败:", repr(e))
    sys.exit(1)

time.sleep(4)

d = get("/api/tasks/" + tid)
t = d.get("task", d)
cfg = t.get("config", {})
mp = cfg.get("max_pages")
print("\n=== 读回配置 ===")
print("max_pages 实际存值 =", mp)
print("状态 =", t.get("status"))
print("pages_total =", t.get("stats", {}).get("pages_total"))
print()
if mp == 1000000:
    print(">>> 结论：1000000 被原样接受 —— 新代码已生效 ✅")
elif mp == 200000:
    print(">>> 结论：被砍成 200000 —— 仍是旧代码 ❌")
else:
    print(">>> 结论：出现意外值", mp)

# 清理：取消任务并删除目录
try:
    post(f"/api/tasks/{tid}/cancel", {})
    print("\n已请求取消该测试任务。")
except Exception as e:
    print("\n取消失败（多半已自行结束）:", repr(e))
print("测试任务目录:", cfg.get("out_root"))
