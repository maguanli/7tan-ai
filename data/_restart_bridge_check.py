# -*- coding: utf-8 -*-
import py_compile, subprocess, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BR = r"D:\7tan\dsh-workspace\oneclick-publish\bridge\publish_bridge.py"
RST = r"D:\7tan\dsh-workspace\oneclick-publish\tools\restart_bridge.py"

try:
    py_compile.compile(BR, doraise=True)
    print("[OK] publish_bridge.py 语法通过")
except Exception as e:
    print("[FAIL] 语法:", e)
    sys.exit(1)

print("--- 重启桥接 ---")
r = subprocess.run([sys.executable, RST], capture_output=True, text=True, errors="ignore", timeout=180)
print(r.stdout[-2000:])
if r.stderr:
    print("stderr:", r.stderr[-600:])
