# -*- coding: utf-8 -*-
import sys, io, json, time, socket, urllib.request, subprocess, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 等服务起来
time.sleep(6)

print("=== 端口 8000 监听情况 ===")
out = subprocess.run("netstat -ano | findstr :8000", shell=True, capture_output=True, text=True).stdout
print(out.strip() or "(无)")

print("\n=== 新进程 ===")
try:
    import psutil
    for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        cl = " ".join(p.info["cmdline"] or [])
        if "run.py" in cl and "8000" in cl:
            print("PID", p.info["pid"], "| start", datetime.datetime.fromtimestamp(p.info["create_time"]))
            print("  cmd:", cl)
except Exception as e:
    print("psutil err:", e)

print("\n=== API 自检 ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:8000/api/tasks", timeout=15)
    d = json.load(r)
    print("HTTP 200, ok =", d.get("ok"), ", 任务数 =", len(d.get("tasks", [])))
except Exception as e:
    print("API 访问失败:", e)

# 读取日志尾部
print("\n=== _server.log 尾部 ===")
try:
    with open("_server.log", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    print("\n".join(lines[-12:]))
except Exception as e:
    print("读日志失败:", e)

print("\n=== _server.err ===")
try:
    txt = open("_server.err", encoding="utf-8", errors="replace").read().strip()
    print(txt[-800:] if txt else "(空)")
except Exception as e:
    print("读err失败:", e)
