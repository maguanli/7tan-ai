# -*- coding: utf-8 -*-
import os, time
base = r'D:\7tan\7tanAI\镜像同事_小说\images'
for root, dirs, files in os.walk(base):
    for f in files:
        if f.lower().endswith('.png') and ('05' in f or '07' in f):
            p = os.path.join(root, f)
            st = os.stat(p)
            print('%s | %dKB | %s | %s' % (p, st.st_size//1024, time.strftime('%m-%d %H:%M:%S', time.localtime(st.st_mtime)), f))
# 也查英文目录的
for f in os.listdir(r'D:\7tan\7tanAI\novel_img'):
    if '05' in f or '07' in f:
        p = os.path.join(r'D:\7tan\7tanAI\novel_img', f)
        st = os.stat(p)
        print('EN: %s | %dKB | %s' % (p, st.st_size//1024, time.strftime('%m-%d %H:%M:%S', time.localtime(st.st_mtime))))
