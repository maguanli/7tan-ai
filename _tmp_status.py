# -*- coding: utf-8 -*-
import subprocess, os, sys, time

print("=== 进程检查 ===")
r = subprocess.run('tasklist /fo csv', shell=True, capture_output=True, text=True, encoding="gbk", errors="replace")
for line in r.stdout.splitlines():
    if any(k in line.lower() for k in ["python", "pyinstaller", "7tan"]):
        print(line.strip())

print("=== build_publish_107.log 尾部 ===")
p = r"D:\7tan\7tanAI\build_publish_107.log"
if os.path.exists(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for l in lines[-20:]:
        print(l)
else:
    print("(无日志)")

print("=== publish_107_patch_log.txt 尾部 ===")
p2 = r"D:\7tan\7tanAI\dist\release\publish_107_patch_log.txt"
if os.path.exists(p2):
    with open(p2, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for l in lines[-20:]:
        print(l)
else:
    print("(无日志)")
