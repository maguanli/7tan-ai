# -*- coding: utf-8 -*-
import os, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

targets = ('v2_top.png', 'v2_sec4.png', 'v2_sec5.png', 'ubb_content.json', 'build_ubb.py', 'build_publish.py')
roots = [r'D:\用户目录\下载\新建文件夹 123', r'D:\7tan', r'D:\用户目录\Desktop']
for root in roots:
    if not os.path.isdir(root):
        continue
    for dp, dn, fn in os.walk(root):
        parts = dp.split(os.sep)
        if any(p in ('.git', 'node_modules', '__pycache__', 'venv', 'site-packages', '7tanAI') for p in parts):
            dn[:] = []
            continue
        for f in fn:
            if f in targets:
                p = os.path.join(dp, f)
                print(time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p))), p)
