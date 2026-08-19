# -*- coding: utf-8 -*-
"""分析输入框区域截图 qq_input_area.png：找边框、内容、颜色分布"""
from PIL import Image

img = Image.open(r'D:\7tan\7tanAI\qq_input_area.png')
W, H = img.size
print('size:', W, H)
px = img.load()

# 找水平边框线（某行大量灰色像素）
print('--- 每10行颜色统计 (x=0..W) ---')
for y in range(0, H, 4):
    whites = grays = darks = 0
    for x in range(W):
        r, g, b = px[x, y][:3]
        if r > 235 and g > 235 and b > 235:
            whites += 1
        elif r < 120 and g < 120 and b < 120:
            darks += 1
        else:
            grays += 1
    print(f'y={y}: w={whites} g={grays} d={darks}')

# 输出非白像素的分布（找文字/图标）
print('--- 非白像素采样 ---')
count = 0
for y in range(0, H, 2):
    row = []
    for x in range(0, W, 2):
        r, g, b = px[x, y][:3]
        if not (r > 235 and g > 235 and b > 235):
            row.append(x)
    if row and count < 40:
        print(f'y={y}: x范围={min(row)}-{max(row)}, 数量={len(row)}')
        count += 1
