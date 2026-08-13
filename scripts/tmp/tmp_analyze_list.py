# -*- coding: utf-8 -*-
"""像素级分析微信联系人列表：按行扫描颜色，找出行边界和高亮行"""
from PIL import ImageGrab

bbox = (300, 130, 620, 860)  # 左侧列表区域
img = ImageGrab.grab(bbox=bbox)
w, h = img.size
px = img.load()

# 在 x=400 处垂直扫描，记录每行(y)的像素颜色
# 微信列表：普通行白色背景，选中行浅灰/浅蓝，分隔线很浅
print("y, color_at_400")
prev_color = None
changes = []
for y in range(0, h, 2):
    r, g, b = px[100, y][:3]  # x=400 屏幕 = 列表内 x=100
    # 简化为亮度
    lum = (r + g + b) // 3
    changes.append((y, r, g, b, lum))

# 输出分段：每 20px 一个采样点
for y in range(0, h, 20):
    r, g, b = px[100, y][:3]
    print(f"y={y} (screen={130+y}): rgb=({r},{g},{b})")

# 找出背景色（白色系）与高亮色（灰色系）的分界
# 统计每个y的亮度，找亮度明显变化的边界
print("\n--- 亮度变化边界 (变化>15) ---")
prev_lum = None
for y, r, g, b, lum in changes:
    if prev_lum is not None and abs(lum - prev_lum) > 15:
        print(f"boundary at y={y} (screen={130+y}), lum {prev_lum}->{lum}")
    prev_lum = lum
