# -*- coding: utf-8 -*-
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import mss
import mss.tools

# 1. 真实光标移动到任务栏右下角"显示桌面"按钮并点击
print("移动鼠标到显示桌面按钮...")
pyautogui.moveTo(1910, 1070, duration=0.8)
time.sleep(0.3)
pyautogui.click()
time.sleep(1.5)

# 2. 截图桌面
with mss.mss() as sct:
    mon = sct.monitors[1]  # 主显示器
    img = sct.grab(mon)
    mss.tools.to_png(img.rgb, img.size, output="desktop.png")
print("桌面已截图: desktop.png")

# 3. 分析蓝色像素块（QQ 图标为蓝色企鹅）
from PIL import Image
im = Image.open("desktop.png").convert("RGB")
w, h = im.size
px = im.load()
print("screen size:", w, h)

# 采样蓝色像素（排除任务栏区域 y > h-70）
blue = []
for y in range(0, h - 70, 3):
    for x in range(0, w, 3):
        r, g, b = px[x, y]
        if b > 140 and (b - r) > 60 and (b - g) > 30:
            blue.append((x, y))

print("蓝色像素点数:", len(blue))

# 网格聚类（90px 格子）
from collections import defaultdict
grid = defaultdict(list)
for x, y in blue:
    grid[(x // 90, y // 90)].append((x, y))

cands = []
for (gx, gy), pts in grid.items():
    if len(pts) < 15:  # 过滤噪声
        continue
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = sum(xs) // len(xs)
    cy = sum(ys) // len(ys)
    cands.append((cx, cy, len(pts), gx, gy))

cands.sort(key=lambda c: -c[2])
print("=== 蓝色图标候选 ===")
for c in cands[:15]:
    print("center=({},{}) 像素数={} 格子=({},{})".format(c[0], c[1], c[2], c[3], c[4]))
