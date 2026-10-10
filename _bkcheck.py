# -*- coding: utf-8 -*-
"""只读：分支状态 + 待备份文件体积。不写任何东西。"""
import subprocess, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = r'D:\7tan\7tanAI'

def git(*a):
    r = subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return (r.stdout or '') + (r.stderr or '')

print('HEAD 分支 :', git('rev-parse', '--abbrev-ref', 'HEAD').strip())
print('领先 origin/develop :', git('rev-list', '--count', 'origin/develop..develop').strip())
print('落后 origin/develop :', git('rev-list', '--count', 'develop..origin/develop').strip())
print()
print('=== 未推送的提交 ===')
print(git('log', '--oneline', 'origin/develop..develop').strip() or '（无）')
print()
print('=== 本地分支 ===')
print(git('branch', '-vv').strip())

print()
print('=== 可疑/大文件体积 ===')
targets = ['_ll_lt.json', '_ll_lthf.json', '_envchk.py', '_gzh1.py',
           '_sohu_report.txt', '_sohu_readback.html', 'serve_gzh.bat',
           '7723/_dump_hf.pkl', '7723/_dump_lt.pkl', '7723/_dump_meta.pkl']
for f in targets:
    p = os.path.join(REPO, f.replace('/', os.sep))
    if os.path.exists(p):
        print('  %8.2f MB  %s' % (os.path.getsize(p) / 1048576.0, f))
    else:
        print('  %8s      %s (不存在)' % '-', f)

print()
print('=== 目录体积 ===')
for d in ['7723', '7723/_scripts', 'hotscan', 'data/watch_shots']:
    p = os.path.join(REPO, d.replace('/', os.sep))
    if not os.path.isdir(p):
        print('  %s (不存在)' % d)
        continue
    n = tot = 0
    for root, _, files in os.walk(p):
        for fn in files:
            try:
                tot += os.path.getsize(os.path.join(root, fn))
                n += 1
            except Exception:
                pass
    print('  %-18s %4d 个文件  %8.2f MB' % (d, n, tot / 1048576.0))
