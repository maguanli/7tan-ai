# -*- coding: utf-8 -*-
import zipfile, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
zpath = r'D:\7tan\7tanAI\dist\release\7tan-web-v1.0.12.zip'
z = zipfile.ZipFile(zpath)
exts = Counter()
for i in z.infolist():
    name = i.filename
    if '.' in name.split('/')[-1]:
        ext = name.rsplit('.', 1)[-1].lower()
        exts[ext] += 1
print('扩展名统计:', dict(exts))
print('---')
# 列出所有不含 .py/.pyd 的文件（可能包含启动器、exe、配置等）
for i in z.infolist():
    n = i.filename
    if not (n.endswith('.py') or n.endswith('.pyd')):
        print(n, i.file_size)
