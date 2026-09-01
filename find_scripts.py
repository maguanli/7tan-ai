# -*- coding: utf-8 -*-
import os
root = r'D:\7tan\7tanAI'
print('=== 查找相关脚本 ===')
for r, ds, fs in os.walk(root):
    # 跳过一些大目录
    if any(x in r for x in ['node_modules', '.git', '__pycache__', 'venv', 'site-packages']):
        continue
    for f in fs:
        if f.endswith('.py') and any(k in f.lower() for k in ['doubao', 'trailer', 'video', 'gen_', 'seedance', 'ark']):
            print(os.path.join(r, f))
