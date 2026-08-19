# -*- coding: utf-8 -*-
"""重新截图窗口 + 分析输入框/发送按钮"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import mss
from mss.tools import to_png
from PIL import Image

# 重新截图窗口 (480,200,1060x640)
with mss.mss() as sct:
    region = {'left': 480, 'top': 200, 'width': 1060, 'height': 640}
    shot = sct.grab(region)
    to_png(shot.rgb, shot.size, output=r'data\screenshots\qq_window2.png')

img = Image.open(r'data\screenshots\qq_window2.png')
w, h = img.size
print('截图尺寸:', w, h)

# 1. 找蓝色发送按钮
print('\n=== 蓝色像素位置（发送按钮）===')
blue_xs = []
blue_ys = []
for y in range(400, h, 2):
    for x in range(400, w, 2):
        r, g, b = img.getpixel((x, y))[:3]
        if b > 200 and r < 100 and 100 < g < 220:
            blue_xs.append(x)
            blue_ys.append(y)
if blue_xs:
    print(f'蓝色 x: {min(blue_xs)}~{max(blue_xs)} -> 屏幕 {480+min(blue_xs)}~{480+max(blue_xs)}')
    print(f'蓝色 y: {min(blue_ys)}~{max(blue_ys)} -> 屏幕 {200+min(blue_ys)}~{200+max(blue_ys)}')

# 2. 找白色输入框区域（每行白色占比）
print('\n=== 底部各行白色占比 ===')
for y in range(480, h, 10):
    white = 0
    total = 0
    for x in range(300, w):
        r, g, b = img.getpixel((x, y))[:3]
        total += 1
        if r > 240 and g > 240 and b > 240:
            white += 1
    print(f'img_y={y} (屏幕{200+y}): 白{white*100//total}%')

# 3. 白色区域 x 范围（找输入框水平边界）
print('\n=== y=770(屏幕) 行白色 x 分布 ===')
for img_y in [550, 570, 590]:
    white_xs = []
    for x in range(300, w):
        r, g, b = img.getpixel((x, img_y))[:3]
        if r > 240 and g > 240 and b > 240:
            white_xs.append(x)
    if white_xs:
        segs = []
        start = prev = white_xs[0]
        for x in white_xs[1:]:
            if x - prev > 8:
                segs.append((start, prev))
                start = x
            prev = x
        segs.append((start, prev))
        print(f'img_y={img_y}(屏幕{200+img_y}): 白色段(窗口x)={segs} -> 屏幕x={[(480+s, 480+e) for s, e in segs]}')
    else:
        print(f'img_y={img_y}: 无白色')
