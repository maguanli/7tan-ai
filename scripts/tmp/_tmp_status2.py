# -*- coding: utf-8 -*-
import subprocess, os, sys, time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=== 相关进程 ===")
r = subprocess.run('tasklist /fo csv', shell=True, capture_output=True, text=True, encoding="gbk", errors="replace")
for line in r.stdout.splitlines():
    if any(k in line.lower() for k in ["python", "pyinstaller"]):
        print(line.strip())

print("=== build_publish_107.log 尾部(20) ===")
p = r"D:\7tan\7tanAI\build_publish_107.log"
if os.path.exists(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for l in lines[-20:]:
        print(l.encode("utf-8", "replace").decode("utf-8", "replace"))
    print(f"(共 {len(lines)} 行, 大小 {os.path.getsize(p)}B, 修改时间 {time.ctime(os.path.getmtime(p))})")
else:
    print("(无日志)")

print("=== publish_107_patch_log.txt 尾部(15) ===")
p2 = r"D:\7tan\7tanAI\dist\release\publish_107_patch_log.txt"
if os.path.exists(p2):
    with open(p2, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for l in lines[-15:]:
        print(l)
    print(f"(共 {len(lines)} 行)")
else:
    print("(无日志)")

print("=== dist/release 文件 ===")
d = r"D:\7tan\7tanAI\dist\release"
if os.path.exists(d):
    for f in os.listdir(d):
        fp = os.path.join(d, f)
        print(f"  {f}  {os.path.getsize(fp)/1048576:.1f}MB  {time.ctime(os.path.getmtime(fp))}")
