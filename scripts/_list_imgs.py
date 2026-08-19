# -*- coding: utf-8 -*-
import os, io, sys, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
roots = [r'D:\7tan\7tanAI\data\screenshots', r'D:\7tan\7tanAI\data',
         r'D:\7tan\7tanAI\downloads', r'D:\7tan\7tanAI\tools\gzh_publish',
         r'D:\7tan\7tanAI\assets', r'D:\7tan\7tanAI\output']
seen = set()
count = 0
for r in roots:
    if not os.path.exists(r):
        print("不存在:", r)
        continue
    for root, dirs, files in os.walk(r):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                p = os.path.join(root, f)
                if p in seen:
                    continue
                seen.add(p)
                count += 1
                sz = os.path.getsize(p)
                t = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%m-%d %H:%M')
                print(f'{t} {sz//1024:>6}KB {p}')
print("总计图片数:", count)
