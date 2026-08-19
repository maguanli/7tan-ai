# -*- coding: utf-8 -*-
"""分析 input_test2.png 找非白色像素（文字痕迹）"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open(r'data\screenshots\input_test2.png')
w, h = img.size
print('截图尺寸:', w, h)

# 统计非白色像素分布（按行）
print('=== 各行非白色像素 ===')
for y in range(0, h, 5):
    nonwhite = []
    for x in range(0, w, 2):
        r, g, b = img.getpixel((x, y))[:3]
        if r < 200 or g < 200 or b < 200:
            nonwhite.append((x, (r, g, b)))
    if len(nonwhite) > 3:
        # 统计颜色
        colors = {}
        for _, c in nonwhite:
            key = ('深' if max(c) < 100 else '中' if max(c) < 160 else '浅')
            colors[key] = colors.get(key, 0) + 1
        print(f'y={y+690}: 非白点{len(nonwhite)} {colors} 前5: {nonwhite[:5]}')
    else:
        print(f'y={y+690}: 干净({len(nonwhite)})')
