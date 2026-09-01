# -*- coding: utf-8 -*-
import os
root = r'D:\7tan\7tanAI\镜像同事_小说'
print('=== 镜像同事_小说 目录下 trailer 相关脚本 ===')
for r, ds, fs in os.walk(root):
    for f in fs:
        if f.endswith('.py') and 'trailer' in f.lower():
            print(os.path.join(r, f))
print()
print('=== 查找 豆包视频设置.txt ===')
for base in [r'D:\7tan\7tanAI', os.path.expanduser('~'), r'D:\7tan\7tanAI\镜像同事_小说']:
    for r, ds, fs in os.walk(base):
        if any(x in r for x in ['node_modules', '.git', '__pycache__', 'venv', 'site-packages']):
            continue
        for f in fs:
            if '豆包' in f or ('视频设置' in f):
                print(os.path.join(r, f))
        if len(r) - len(base) > 200:
            break
