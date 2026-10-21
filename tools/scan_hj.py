# -*- coding: utf-8 -*-
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = r'D:\用户目录\下载\新建文件夹 123\游戏资料'
imgs = sorted(f for f in os.listdir(SRC) if f.lower().endswith(('.jpg', '.jpeg', '.png')))
print('SRC total imgs:', len(imgs))
for f in imgs:
    print('  ', f, os.path.getsize(os.path.join(SRC, f)) // 1024, 'KB')

print()
print('=== find article dirs (hongjing / 红警) ===')
root = r'D:\用户目录\下载\新建文件夹 123'
for dp, dn, fn in os.walk(root):
    if '.git' in dp:
        continue
    low = dp.lower()
    if 'hongjing' in low or 'hong-jing' in low or 'hongzheng' in low:
        print('DIR:', dp)
        for f in sorted(fn):
            print('     ', f, os.path.getsize(os.path.join(dp, f)) // 1024, 'KB')
        if dp.count(os.sep) > 6:
            dn[:] = []
