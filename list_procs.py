# -*- coding: utf-8 -*-
"""列出相关进程"""
import subprocess, os

out = subprocess.run(["tasklist", "/FO", "CSV"], capture_output=True, text=True,
                     encoding="utf-8", errors="replace").stdout
for line in out.splitlines():
    low = line.lower()
    if any(k in low for k in ["7tan", "python", "webengine", "pyinstaller"]):
        print(line)
