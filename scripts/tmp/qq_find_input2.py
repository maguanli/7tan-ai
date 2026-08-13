# -*- coding: utf-8 -*-
"""细化：找出QQ底部区域非白像素分布，判断输入框/工具栏位置"""
from PIL import Image

img = Image.open(r'D:\7tan\7tanAI\qq_full_now.png')
W, H = img.size
px = img.load()

# 扫描 x=260-920, y=580-640，记录非白像素列分布
from collections import Counter
col_nonwhite = Counter()
samples = []
for y in range(580, 640):
    for x in range(260, 920):
        r, g, b = px[x, y][:3]
        if not (r > 235 and g > 235 and b > 235):
            col_nonwhite[x] += 1
            if len(samples) < 300:
                samples.append((x + 460, y + 200, r, g, b))

print('非白列分布（x屏幕坐标: 行数）')
for x in sorted(col_nonwhite):
    c = col_nonwhite[x]
    if c > 3:
        print(f'  x={x+460}: {c}行')
print()
print('采样像素（屏幕x, 屏幕y, rgb）前60个:')
for s in samples[:60]:
    print(f'  {s}')
