# -*- coding: utf-8 -*-
"""像素分析：定位微信窗口顶部搜索框（浅灰圆角矩形）"""
import ctypes, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
from PIL import Image

WX = (351, 149, 968, 645)

with mss.mss() as sct:
    shot = sct.grab({"left": WX[0], "top": WX[1], "width": WX[2], "height": WX[3]})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_window.png")
print(f"截图尺寸: {img.size}")

# 分析顶部 120px 的像素，找"浅灰矩形"（搜索框）
import collections
w, h = img.size
top_h = 120
# 统计每行像素颜色分布，找与白色背景不同的浅灰区域
for y in range(0, top_h, 5):
    row_colors = collections.Counter()
    for x in range(0, w, 3):
        row_colors[img.getpixel((x, y))] += 1
    top3 = row_colors.most_common(3)
    print(f"y={y:3d}: {top3}")

# 分析整列浅灰矩形：找背景色与元素色交界
# 先找搜索框可能区域：x 范围 0~400, y 范围 0~110
print("\n=== 左侧区域颜色扫描 (x=0..400, y=0..110) ===")
for y in range(10, 110, 8):
    vals = []
    for x in range(0, 400, 20):
        vals.append(img.getpixel((x, y)))
    # 简化显示
    print(f"y={y:3d}: {vals[:10]}")
