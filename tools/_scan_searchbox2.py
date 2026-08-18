# -*- coding: utf-8 -*-
"""精细扫描左侧栏顶部区域，找搜索框圆角矩形边界"""
import sys, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
from PIL import Image

WX = (351, 149, 968, 645)
with mss.mss() as sct:
    shot = sct.grab({"left": WX[0], "top": WX[1], "width": WX[2], "height": WX[3]})
img = Image.frombytes("RGB", shot.size, shot.rgb)

# 左侧栏顶部区域 (相对窗口坐标)
region = img.crop((60, 30, 320, 115))
region.save(r"D:\7tan\7tanAI\data\screenshots\searchbox_region.png")

# 统计该区域所有颜色及其分布
import collections
colors = collections.Counter()
for y in range(region.height):
    for x in range(region.width):
        colors[region.getpixel((x, y))] += 1

print("=== 左侧栏顶部区域颜色统计（top 15）===")
for c, n in colors.most_common(15):
    print(f"  {c}: {n}")

# 找"非背景色"（背景 #EEEEF0）的连通块
BG = (238, 238, 240)
def is_bg(px):
    return abs(px[0]-BG[0])<=3 and abs(px[1]-BG[1])<=3 and abs(px[2]-BG[2])<=3

# 按行分析非背景像素的 x 范围
print("\n=== 每行非背景色 x 范围（区域 60~320, 30~115）===")
for y in range(region.height):
    xs = [x for x in range(region.width) if not is_bg(region.getpixel((x, y)))]
    if xs:
        # 压缩显示
        x0, x1 = xs[0], xs[-1]
        n = len(xs)
        print(f"y={y+30:3d}: 非背景{n:3d}个 x=[{x0+60},{x1+60}]")
