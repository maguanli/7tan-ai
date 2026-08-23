# -*- coding: utf-8 -*-
import os, shutil
src_dir = r'D:\7tan\7tanAI\镜像同事_小说\images'
dst_dir = r'D:\7tan\7tanAI\novel_img'
os.makedirs(dst_dir, exist_ok=True)
# 把 images 目录下所有 png 递归复制到英文目录（覆盖已存在的）
copied = []
for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.lower().endswith('.png'):
            src = os.path.join(root, f)
            dst = os.path.join(dst_dir, f)
            shutil.copy2(src, dst)
            copied.append(f)
print('copied', len(copied))
for c in sorted(copied):
    print(' ', c)
