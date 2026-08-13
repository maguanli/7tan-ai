# -*- coding: utf-8 -*-
import os, io, sys, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
print("cpu_count:", os.cpu_count())
r = subprocess.run(["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
print(r.stdout)
