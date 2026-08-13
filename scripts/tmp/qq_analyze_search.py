# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image
from collections import defaultdict

im = Image.open("search_result.png").convert("RGB")
w, h = im.size
px = im.load()
print("size:", w, h)

# 蓝色像素检测（QQ图标蓝色系 #12B7F5: r18 g183 b245）
blue = []
for y in range(0, h - 60, 2):
    for x in range(0, w, 2):
        r, g, b = px[x, y]
        if b > 150 and (b - r) > 80 and (b - g) > 40:
            blue.append((x, y))

print("蓝色像素点数:", len(blue))

# 聚类 80px 格子
grid = defaultdict(list)
for x, y in blue:
    grid[(x // 80, y // 80)].append((x, y))

cands = []
for (gx, gy), pts in grid.items():
    if len(pts) < 30:
        continue
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cands.append((sum(xs)//len(xs), sum(ys)//len(ys), len(pts), gx, gy))

cands.sort(key=lambda c: -c[2])
print("=== 蓝色块候选（疑似QQ图标）===")
for c in cands[:10]:
    print("center=({},{}) px={} grid=({},{})".format(c[0], c[1], c[2], c[3], c[4]))
