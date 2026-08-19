# -*- coding: utf-8 -*-
"""查父进程链 + 日志中两个实例的活跃痕迹"""
import subprocess, sys, json, re, os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("1. 进程树（13248 的父进程 2772 是谁）")
print("=" * 60)
ps = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @(2772,13248,11948)} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=60)
out = ps.stdout.strip()
try:
    data = json.loads(out)
    if isinstance(data, dict):
        data = [data]
    for p in data:
        print(f"PID={p.get('ProcessId')}  父={p.get('ParentProcessId')}  {p.get('Name')}")
        print(f"    EXE={p.get('ExecutablePath')}")
        print(f"    CMD={(p.get('CommandLine') or '')[:180]}")
        print()
except Exception as e:
    print("解析失败:", e)
    print(out[:1500])

print("=" * 60)
print("2. 今日日志中记录的 PID（找两个实例的活动痕迹）")
print("=" * 60)
log = r'D:\7tan\7tanAI\logs\app_2026-08-14.log'
if os.path.exists(log):
    with open(log, encoding='utf-8', errors='ignore') as fp:
        lines = fp.readlines()
    # 统计日志里出现的 PID 数字
    pids = {}
    for line in lines[-300:]:
        m = re.findall(r'\b(?:PID|pid|进程|Process)[=:：]\s*(\d+)', line, re.I)
        for pid in m:
            pids[pid] = pids.get(pid, 0) + 1
    if pids:
        for pid, cnt in sorted(pids.items(), key=lambda x: -x[1]):
            print(f"  日志提到 PID={pid}  {cnt} 次")
    else:
        print("  日志尾部未发现 PID 标记")
    # 打印最后 15 行看活动
    print("--- 日志最后 15 行 ---")
    for line in lines[-15:]:
        print("  " + line.rstrip()[:160])

print("=" * 60)
print("3. 检查 .venv 与系统 python 的 main.py 是否同一份")
print("=" * 60)
for p in [r'D:\7tan\7tanAI\main.py', r'D:\7tan\7tanAI\.venv\Scripts\python.exe']:
    if os.path.exists(p):
        st = os.stat(p)
        print(f"  {p}")
        print(f"      大小={st.st_size}  修改时间={st.st_mtime}")

print("=" * 60)
print("4. 最近 10 分钟 git 仓库是否有新提交/操作")
print("=" * 60)
r = subprocess.run(['git', '-C', r'D:\7tan\7tanAI', 'log', '--oneline', '-5'],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
print(r.stdout or r.stderr)
