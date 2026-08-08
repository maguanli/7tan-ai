# -*- coding: utf-8 -*-
"""精确定位输入框和发送按钮的 x 范围"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open(r'data\screenshots\qq_window.png')
w, h = img.size

def color_at(x, y):
    px = img.getpixel((x, y))
    r, g, b = px[:3]
    return r, g, b

# 找蓝色像素（发送按钮）
print('=== y=810 行的蓝色像素 x 分布 ===')
blue_xs = []
for x in range(0, w):
    r, g, b = color_at(x, 610)  # 窗口内 y=610 = 屏幕 810
    if b > 200 and r < 100 and g > 100:
        blue_xs.append(x)
if blue_xs:
    print(f'蓝色像素 x 范围: {min(blue_xs)}~{max(blue_xs)} (屏幕 {480+min(blue_xs)}~{480+max(blue_xs)})')
else:
    print('未找到蓝色像素')

# 找输入框白色区域范围（y=750, 屏幕 750 = 窗口 550）
print('\n=== y=750 行的颜色分布（找输入框边界）===')
white_xs = []
for x in range(0, w):
    r, g, b = color_at(x, 550)
    if r > 245 and g > 245 and b > 245:
        white_xs.append(x)
if white_xs:
    # 找连续白色段
    segments = []
    start = white_xs[0]
    prev = white_xs[0]
    for x in white_xs[1:]:
        if x - prev > 5:
            segments.append((start, prev))
            start = x
        prev = x
    segments.append((start, prev))
    print(f'白色段: {[(s, e, f"屏幕x={480+s}~{480+e}") for s, e in segments]}')
else:
    print('无白色像素')

# 输入框垂直范围：x=1150(窗口670) 列的白色像素 y 范围
print('\n=== x=1150(窗口x=670) 列的白色区域 ===')
white_ys = []
for y in range(300, h):
    r, g, b = color_at(670, y)
    if r > 245 and g > 245 and b > 245:
        white_ys.append(y)
if white_ys:
    print(f'白色 y 范围: {min(white_ys)}~{max(white_ys)} (屏幕 {200+min(white_ys)}~{200+max(white_ys)})')
else:
    print('无')
