# -*- coding: utf-8 -*-
import subprocess, io, sys, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 1) 查 7860/7861 端口占用
r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
pids = set()
for line in r.stdout.splitlines():
    if ":7860" in line or ":7861" in line:
        print("LINE:", line.strip())
        m = re.findall(r"(\d+)\s*$", line.strip())
        if m:
            pids.add(m[-1])

print("PIDs to kill:", pids)
for pid in pids:
    rr = subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    print("kill", pid, "->", rr.returncode, (rr.stdout or rr.stderr).strip())

# 2) 确认端口释放
r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
left = [l for l in r.stdout.splitlines() if ":7860" in l or ":7861" in l]
print("remaining:", left if left else "NONE (ports free)")
