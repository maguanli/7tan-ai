# -*- coding: utf-8 -*-
"""检查 BASE 路径编码和 images 目录真实文件名"""
import os

BASE = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说')
print("BASE repr:", repr(BASE))
print("BASE exists:", os.path.exists(BASE))

imgs = os.path.join(BASE, 'images')
print("IMGS exists:", os.path.exists(imgs))
if os.path.exists(imgs):
    names = os.listdir(imgs)
    print("count:", len(names))
    for n in sorted(names):
        print("  ", repr(n), os.path.getsize(os.path.join(imgs, n)) if os.path.isfile(os.path.join(imgs, n)) else "(dir)")

# 直接构造 ASCII 路径拼 BASE 验证
p = os.path.join(imgs, 'ch01_02.png')
print("join exists:", os.path.exists(p), "| path repr:", repr(p))

# 用 os.scandir 看原始
print("\nscandir 前5项:")
for i, e in enumerate(os.scandir(imgs)):
    if i >= 5:
        break
    print("  ", repr(e.name))
