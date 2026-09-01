# -*- coding: utf-8 -*-
import os
p = r'D:\7tan\7tanAI\镜像同事_小说\定妆图'
print('=== 定妆图目录 ===')
if os.path.isdir(p):
    for f in sorted(os.listdir(p)):
        full = os.path.join(p, f)
        size = os.path.getsize(full) if os.path.isfile(full) else 0
        print(f'  {f}  ({size} bytes)')
else:
    print('  目录不存在!')

print()
print('=== video 目录 ===')
v = r'D:\7tan\7tanAI\镜像同事_小说\video'
if os.path.isdir(v):
    for d in sorted(os.listdir(v)):
        full = os.path.join(v, d)
        if os.path.isdir(full):
            print(f'[{d}]')
            for f in sorted(os.listdir(full)):
                print(f'    {f}')
        else:
            print(f'  {d}')
else:
    print('  video 目录不存在!')
