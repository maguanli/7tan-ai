# -*- coding: utf-8 -*-
"""只读：定位含 key 的提交与目录。不写任何东西。"""
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = r'D:\7tan\7tanAI'
KEY = 'ark-200c72f8-1b6f-4b16-8fae-9fcddb905182-72f87'
KEY2 = 'ark-532b329a-8d6a-4940-8c3a-aaff705ffcb1-9bbac'

def git(*a):
    r = subprocess.run(['git', '-c', 'core.quotepath=false'] + list(a), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return (r.stdout or '') + (r.stderr or '')

print('=== 引入 key1 的提交（全库） ===')
print(git('log', '--oneline', '--all', '-S', KEY).strip() or '（无）')
print()
print('=== 引入 key2 的提交（全库） ===')
print(git('log', '--oneline', '--all', '-S', KEY2).strip() or '（无）')
print()
print('=== origin/develop..develop 区间内，含 key 的提交 ===')
print(git('log', '--oneline', '-S', KEY, 'origin/develop..develop').strip() or '（无）')
print(git('log', '--oneline', '-S', KEY2, 'origin/develop..develop').strip() or '（无）')
print()
print('=== 这些文件当前在 HEAD 里的完整路径 ===')
print(git('grep', '-l', '-I', '-E', 'ark-[0-9a-fA-F-]{16,}', 'develop').strip())
print()
print('=== 工作区里 ' + '《国民周报_小说》'.encode('utf-8').decode('utf-8') + ' 目录是否存在 ===')
import os
for name in os.listdir(REPO):
    if '小说' in name or 'ARK' in name.upper():
        print('   ', name)
