# -*- coding: utf-8 -*-
import os, time
p = r"D:\7tan\7tanAI\dist\build_verify_log.txt"
data = open(p, "rb").read()
text = data.decode("utf-8", errors="replace")
lines = [l for l in text.splitlines() if l.strip()]
print("lines:", len(lines))
print("--- last 6 ---")
for l in lines[-6:]:
    try:
        print(l[:160])
    except Exception:
        pass
# 进程是否存活
import subprocess
r = subprocess.run(["tasklist", "/FI", "PID eq 1940"], capture_output=True, text=True, encoding="utf-8", errors="replace")
alive = "1940" in r.stdout
print("pyinstaller 进程存活:", alive)
