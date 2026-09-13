# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from ocr_locate_click import full_screen_image

img = full_screen_image()
# 编辑区：x 380~950, y 250~1000
crop = img.crop((380, 250, 950, 1000))
crop.save(r"D:\7tan\7tanAI\data\screenshots\editor_area.png")
print("saved editor_area.png", crop.size)

gray = crop.convert("L")
w, h = gray.size
px = gray.load()

# 1) 整体统计
total = w * h
dark = sum(1 for y in range(h) for x in range(w) if px[x, y] < 100)
nonwhite = sum(1 for y in range(h) for x in range(w) if px[x, y] < 235)
print(f"size={w}x{h}  dark(<100)={dark} ({dark/total*100:.1f}%)  nonwhite(<235)={nonwhite} ({nonwhite/total*100:.1f}%)")

# 2) 按行扫描深色像素分布（找图片块）
rows = []
for y in range(h):
    cnt = sum(1 for x in range(w) if px[x, y] < 100)
    rows.append(cnt)
# 找连续深色行段（每行深色像素>30 的行）
segments = []
start = None
for y in range(h):
    if rows[y] > 30:
        if start is None:
            start = y
    else:
        if start is not None:
            segments.append((start, y - 1))
            start = None
if start is not None:
    segments.append((start, h - 1))
print("dark segments (rows with >30 dark px):")
for s in segments:
    print(f"  y={250+s[0]}~{250+s[1]} (height {s[1]-s[0]+1}px)")

# 3) 彩色检测：饱和度较高的像素（金色/深蓝卡片）
sat = 0
for y in range(0, h, 4):
    for x in range(0, w, 4):
        r, g, b = crop.getpixel((x, y))[:3]
        mx, mn = max(r, g, b), min(r, g, b)
        if mx - mn > 40:
            sat += 1
print(f"colorful samples (sat>40): {sat} (sampled 1/16)")
