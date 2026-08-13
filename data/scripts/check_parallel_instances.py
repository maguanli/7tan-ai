# -*- coding: utf-8 -*-
"""检查是否有并行 AI/工具实例在操作同一仓库"""
import subprocess, os, re, glob

print("=" * 60)
print("1. 当前相关进程（python/git/node/7tan）")
print("=" * 60)
try:
    r = subprocess.run(['tasklist', '/FO', 'CSV'], capture_output=True, text=True, encoding='gbk', errors='ignore')
    for line in r.stdout.splitlines():
        parts = line.split('","')
        if len(parts) >= 2:
            name = parts[0].strip('"').lower()
            pid = parts[1].strip('"') if len(parts) > 1 else '?'
            if any(k in name for k in ['python', 'git', 'node', '7tan']):
                print(f"  PID={pid:<8} {name}")
except Exception as e:
    print("  进程查询失败:", e)

print()
print("=" * 60)
print("2. 7tanAI 实例痕迹（运行目录、锁文件、.pid）")
print("=" * 60)
base = r'D:\7tan'
if os.path.isdir(base):
    for name in os.listdir(base):
        full = os.path.join(base, name)
        if os.path.isdir(full):
            # 检查是否有 app 运行特征文件
            markers = [m for m in ['7tanAI.exe', 'main.py', 'app.py', 'config.yaml'] if os.path.exists(os.path.join(full, m))]
            if markers:
                print(f"  [目录] {name}  (含 {', '.join(markers)})")

# 查找可能的锁文件
print()
print("3. 查找 .pid / .lock / 运行锁")
for root, dirs, files in os.walk(base):
    # 跳过 .git 和 node_modules 等大目录
    dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'venv', '__pycache__', '.venv')]
    for f in files:
        if f.endswith(('.pid', '.lock', '.running')) or 'instance' in f.lower():
            print(f"  {os.path.join(root, f)}")
    if root.count(os.sep) - base.count(os.sep) > 2:
        dirs[:] = []

print()
print("=" * 60)
print("4. 今日日志 app_2026-08-14.log 尾部（看是否有第二实例活动）")
print("=" * 60)
log = os.path.join(base, '7tanAI', 'logs', 'app_2026-08-14.log')
if os.path.exists(log):
    with open(log, encoding='utf-8', errors='ignore') as fp:
        lines = fp.readlines()
    print("".join(lines[-40:]))
else:
    print("  今日日志不存在")
