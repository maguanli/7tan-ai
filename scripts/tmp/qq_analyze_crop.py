# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image
from collections import defaultdict

im = Image.open("search_crop.png").convert("RGB")
w, h = im.size
px = im.load()
print("search_crop size:", w, h)

# 1. 整体颜色分布（前10主色）
colors = defaultdict(int)
for y in range(0, h, 4):
    for x in range(0, w, 4):
        colors[px[x, y]] += 1
print("=== 主色 TOP10 ===")
for c, n in sorted(colors.items(), key=lambda kv: -kv[1])[:10]:
    print("RGB{} : {} 点".format(c, n))

# 2. 找蓝色像素块（QQ图标蓝）
print("=== 蓝色块分析（QQ图标候选）===")
blue = []
for y in range(0, h, 2):
    for x in range(0, w, 2):
        r, g, b = px[x, y]
        # QQ 蓝 #12B7F5 或深蓝图标
        if b > 130 and (b - r) > 50 and (b - g) > 20:
            blue.append((x, y))
print("蓝色点数:", len(blue))

grid = defaultdict(list)
for x, y in blue:
    grid[(x // 70, y // 70)].append((x, y))
cands = []
for (gx, gy), pts in grid.items():
    if len(pts) < 20:
        continue
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cands.append((sum(xs)//len(xs), sum(ys)//len(ys), len(pts)))
cands.sort(key=lambda c: -c[2])
for c in cands[:10]:
    # 换算回屏幕坐标：裁剪原点(30,440)，放大2倍
    sx = 30 + c[0] // 2
    sy = 440 + c[1] // 2
    print("裁剪内center=({},{}) px={} -> 屏幕坐标=({},{})".format(c[0], c[1], c[2], sx, sy))
