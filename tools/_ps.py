# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
pids = ["3112", "8724", "7300", "3820", "10180", "4964", "4280"]
out = subprocess.run(["tasklist"], capture_output=True, text=True, encoding="gbk", errors="replace").stdout
for line in out.splitlines():
    if any(pid in line for pid in pids):
        print(line)
