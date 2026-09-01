# -*- coding: utf-8 -*-
import os
targets = []
home = os.path.expanduser('~')
candidates = [
    os.path.join(home, 'Desktop'),
    os.path.join(home, 'OneDrive', 'Desktop'),
    r'D:\7tan\7tanAI',
    r'D:\7tan\7tanAI' + os.sep + '镜像同事_小说',
    'D:\\',
]
for base in candidates:
    if not os.path.isdir(base):
        continue
    for r, ds, fs in os.walk(base):
        depth = r[len(base):].count(os.sep)
        if depth > 3:
            continue
        if any(x in r for x in ['node_modules', '.git', '__pycache__', 'venv', 'site-packages', 'dist']):
            continue
        for f in fs:
            if '豆包' in f or '视频设置' in f or ('doubao' in f.lower() and f.endswith('.txt')):
                targets.append(os.path.join(r, f))
seen = set()
for t in targets:
    if t not in seen:
        seen.add(t)
        print(t)
if not targets:
    print('未找到')
