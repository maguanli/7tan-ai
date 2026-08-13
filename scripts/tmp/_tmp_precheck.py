# -*- coding: utf-8 -*-
"""发布前检查：进程占用、pyd 锁定、目录占用"""
import os, sys, subprocess

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, encoding="gbk", errors="replace")
        return r.stdout + r.stderr
    except Exception as e:
        return f"ERR {e}"

print("=== 1. 进程列表 (7tan/editor) ===")
print(run('tasklist /fo csv | findstr /i "7tan editor"'))

print("=== 2. 进程路径 ===")
print(run('wmic process get ProcessId,Name,ExecutablePath /format:csv 2>nul | findstr /i "7tan editor"'))

print("=== 3. pyd 可写性测试 ===")
dst = r"D:\7tan\7tanAI\src\security\auth_client.pyd"
try:
    with open(dst, "ab") as f:
        pass
    print("  auth_client.pyd 可写（未被锁定）✅")
except PermissionError as e:
    print("  auth_client.pyd 被锁定 ❌ PermissionError")
except Exception as e:
    print(f"  其他错误: {e}")

print("=== 4. 目录占用 ===")
for d in [r"D:\7tan\7tanAI\build", r"D:\7tan\7tanAI\dist", r"D:\7tan\7tanAI\dist\release", r"D:\7tan\7tanAI\dist\7tan-editor"]:
    total = 0
    for root, dirs, files in os.walk(d):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    print(f"  {d}: {total/1048576:.1f} MB")

print("=== 5. 磁盘剩余 ===")
import shutil
t = shutil.disk_usage("D:\\")
print(f"  D盘剩余: {t.free/1073741824:.1f} GB / 总 {t.total/1073741824:.1f} GB")

print("=== 6. 新版 pyd 时间戳 ===")
src = r"D:\7tan\7tanAI\tools\_tmp_authbuild\auth_client.pyd"
dst = r"D:\7tan\7tanAI\src\security\auth_client.pyd"
print(f"  新版(tools): {os.path.getmtime(src):.0f}  size={os.path.getsize(src)}")
print(f"  当前(src):   {os.path.getmtime(dst):.0f}  size={os.path.getsize(dst)}")
