# -*- coding: utf-8 -*-
"""分析输入框截图深色像素分布：文字 vs 图标"""
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

img = Image.open(r'D:\7tan\7tanAI\scripts\qq_input_after_paste2.png').convert('L')
w, h = img.size
px = img.load()

# 深色像素按 x 分段统计
print('=== 深色像素 x 分布（每30px） ===')
for x in range(0, w, 30):
    cnt = 0
    for yy in range(h):
        for xx in range(x, min(x + 30, w)):
            if px[xx, yy] < 128:
                cnt += 1
    if cnt > 20:
        print(f'  x={x}-{x+30}: {cnt}')

# 深色像素按 y 分段统计
print('=== 深色像素 y 分布（每10px） ===')
for y in range(0, h, 10):
    cnt = 0
    for yy in range(y, min(y + 10, h)):
        for xx in range(w):
            if px[xx, yy] < 128:
                cnt += 1
    if cnt > 20:
        print(f'  y={y}-{y+10}: {cnt}')

# 找文字行（连续深色像素 > 3 的行，文字特征）
print('=== 疑似文字行（深色像素>30且连续） ===')
for y in range(h):
    cnt = sum(1 for xx in range(w) if px[xx, y] < 128)
    if cnt > 30:
        print(f'  y={y}: {cnt}px')
