# -*- coding: utf-8 -*-
"""扫描聊天区底部找输入框边界（灰线/边框）"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open(r'data\screenshots\qq_after_click.png')
w, h = img.size

# 扫描 x=850-1350 (窗口 x=370-870)，y=550-840 (窗口 y=350-640)
print('=== 每行颜色变化检测（找分割线/输入框边界）===')
for y in range(350, 640, 2):
    colors = set()
    for x in range(370, 870, 4):
        r, g, b = img.getpixel((x, y))[:3]
        colors.add((r // 20 * 20, g // 20 * 20, b // 20 * 20))
    # 主要颜色数
    if len(colors) > 2:
        print(f'y={200+y} (屏幕): 颜色数={len(colors)} {sorted(colors)[:6]}')
    elif len(colors) == 2 and y > 450:
        print(f'y={200+y} (屏幕): 2色 {sorted(colors)}')

print('\n=== 详细：x=900 列 y=600-840 ===')
for y in range(600, 841, 5):
    r, g, b = img.getpixel((420, y - 200))[:3]
    print(f'y={y}: ({r},{g},{b})')
