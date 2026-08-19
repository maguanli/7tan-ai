# -*- coding: utf-8 -*-
"""分析 qq_after_click.png 找输入框和发送按钮"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open(r'data\screenshots\qq_after_click.png')
w, h = img.size
print('截图尺寸:', w, h)

# 1. 找蓝色发送按钮
print('=== 蓝色像素（发送按钮）===')
blue_points = []
for y in range(500, h, 1):
    for x in range(300, w, 1):
        r, g, b = img.getpixel((x, y))[:3]
        if b > 190 and r < 110 and g > 100:
            blue_points.append((x, y))
if blue_points:
    xs = [p[0] for p in blue_points]
    ys = [p[1] for p in blue_points]
    print(f'窗口内 x: {min(xs)}~{max(xs)} -> 屏幕 {480+min(xs)}~{480+max(xs)}')
    print(f'窗口内 y: {min(ys)}~{max(ys)} -> 屏幕 {200+min(ys)}~{200+max(ys)}')
else:
    print('无蓝色像素')

# 2. 找输入框（浅色区域在深色聊天背景下的分界）
# 扫描 x=900-1300 列，找各行颜色
print('\n=== x=1000 列颜色随 y 变化 ===')
prev = None
for y in range(500, h, 5):
    r, g, b = img.getpixel((520, y))[:3]  # 窗口 x=520 -> 屏幕 1000
    key = ('白' if r > 235 and g > 235 and b > 235 else
           '灰' if abs(r-g) < 20 and abs(g-b) < 20 else
           '色')
    if key != prev:
        print(f'  y={200+y}: {key} ({r},{g},{b})')
        prev = key

# 3. 检查底部工具栏区域
print('\n=== 底部工具栏图标（y=760-840 屏幕）===\n')
for y in [760, 780, 800, 820, 830]:
    row = []
    for x in range(300, w, 20):
        r, g, b = img.getpixel((x, y-200))[:3]
        if r < 150 or g < 150 or b < 150:
            row.append((480+x, (r, g, b)))
    if row:
        print(f'y={y}: 深色点 {row[:12]}')
    else:
        print(f'y={y}: 全浅色')
