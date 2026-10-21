# -*- coding: utf-8 -*-
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

root = r'D:\用户目录\下载\新建文件夹 123'
for dp, dn, fn in os.walk(root):
    parts = dp.split(os.sep)
    if '.git' in parts or 'node_modules' in parts:
        dn[:] = []
        continue
    if dp.count(os.sep) > 8:
        dn[:] = []
    for f in fn:
        if f in ('article.md', 'ubb_content.json') or f.startswith('公众号版'):
            print(os.path.join(dp, f))
