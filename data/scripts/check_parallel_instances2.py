# -*- coding: utf-8 -*-
"""深入检查进程命令行身份 + 实例锁"""
import subprocess, os, sys, json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("1. 各 python/node 进程的命令行（确认身份）")
print("=" * 60)
ps = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|node'} | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"],
    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=60)
out = ps.stdout.strip()
try:
    data = json.loads(out)
    if isinstance(data, dict):
        data = [data]
    for p in data:
        pid = p.get('ProcessId')
        name = p.get('Name')
        cmd = (p.get('CommandLine') or '')[:200]
        print(f"  PID={pid}  {name}")
        print(f"      CMD: {cmd}")
except Exception as e:
    print("  解析失败:", e)
    print("  原始输出:", out[:2000])

print()
print("=" * 60)
print("2. 实例锁文件内容")
print("=" * 60)
lock_path = r'D:\7tan\7tanAI\data\.instance.lock'
if os.path.exists(lock_path):
    with open(lock_path, 'rb') as fp:
        raw = fp.read()
    print(f"  大小: {len(raw)} 字节")
    print(f"  内容: {raw[:300]!r}")
else:
    print("  锁文件不存在")

print()
print("=" * 60)
print("3. 今日日志最后 40 行（utf-8 输出）")
print("=" * 60)
log = r'D:\7tan\7tanAI\logs\app_2026-08-14.log'
if os.path.exists(log):
    with open(log, encoding='utf-8', errors='ignore') as fp:
        lines = fp.readlines()
    for line in lines[-40:]:
        print("  " + line.rstrip())
else:
    print("  今日日志不存在")
