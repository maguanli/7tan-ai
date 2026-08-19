# -*- coding: utf-8 -*-
import subprocess, io, sys, os, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
time.sleep(5)
r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
left = [l for l in r.stdout.splitlines() if ":7860" in l or ":7861" in l]
print(left if left else "PORTS FREE")
