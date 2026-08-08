# -*- coding: utf-8 -*-
"""像素级分析：在桌面截图区域找 QQ 图标（彩色图形）的中心"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from PIL import Image
import collections

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\_desktop_now.png").convert("RGB")
W, H = img.size
print("全屏:", W, H)

# 分析 QQ 图标所在网格块 (0,560)-(120,700)
box = (0, 550, 130, 710)
crop = img.crop(box)
px = crop.load()

# 统计最常见颜色（背景色）
counter = collections.Counter()
for y in range(crop.height):
    for x in range(crop.width):
        counter[px[x, y]] += 1
bg_color, bg_count = counter.most_common(1)[0]
print("背景色:", bg_color, "占比:", bg_count / (crop.width * crop.height) * 100, "%")

# 找出非背景色像素的包围盒
min_x, min_y, max_x, max_y = 9999, 9999, -1, -1
pixels = []
for y in range(crop.height):
    for x in range(crop.width):
        c = px[x, y]
        # 与背景色差异较大的像素
        diff = abs(c[0]-bg_color[0]) + abs(c[1]-bg_color[1]) + abs(c[2]-bg_color[2])
        if diff > 60:
            pixels.append((x, y))
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x), max(max_y, y)

print(f"非背景像素数: {len(pixels)}")
if pixels:
    print(f"非背景像素包围盒: ({min_x},{min_y}) - ({max_x},{max_y}) (块内坐标)")
    # 块内坐标转全屏坐标
    ox0, oy0 = box[0], box[1]
    cx = ox0 + (min_x + max_x) // 2
    cy = oy0 + (min_y + max_y) // 2
    print(f"图形中心(全屏): ({cx},{cy})")
    print(f"图形范围(全屏): x {ox0+min_x}-{ox0+max_x}, y {oy0+min_y}-{oy0+max_y}")

    # 按 y 分段，看看是否有多个图形（图标+文字）
    # 输出每 20px 一行的非背景像素数
    print("\n每20px行的非背景像素数:")
    prev_y = None
    for y in range(min_y, max_y + 1, 5):
        count_in_row = sum(1 for (x2, y2) in pixels if y2 == y)
        if count_in_row:
            print(f"  y={oy0+y}: {count_in_row}px")
