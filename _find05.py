# -*- coding: utf-8 -*-
import os
# 搜索整个 7tan 目录下所有 ch01_05 文件
hits = []
for root, dirs, files in os.walk(r'D:\7tan\7tanAI'):
    # 跳过 node_modules 等大目录
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.venv', '.git', 'build', 'dist', 'logs', '__pycache__')]
    for f in files:
        if 'ch01_05' in f or 'ch0105' in f.lower() or 'tmp_check' in f:
            hits.append(os.path.join(root, f))
for h in hits:
    print(repr(h))
print('total:', len(hits))
