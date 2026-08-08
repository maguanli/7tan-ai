# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
import mss.tools
from PIL import Image, ImageChops

# 截当前任务栏
with mss.mss() as sct:
    mon = sct.monitors[1]
    tb = {"left": mon["left"], "top": mon["top"] + mon["height"] - 60, "width": mon["width"], "height": 60}
    img = sct.grab(tb)
    mss.tools.to_png(img.rgb, img.size, output="taskbar_now.png")
print("taskbar_now.png saved")

old = Image.open("taskbar.png").convert("RGB")
new = Image.open("taskbar_now.png").convert("RGB")
w, h = old.size
print("taskbar size:", w, h)

# 逐列计算差异量（排除右下角时钟区域 x>1750）
col_diff = []
for x in range(0, w):
    d = 0
    for y in range(0, h, 2):
        po = old.getpixel((x, y))
        pn = new.getpixel((x, y))
        d += abs(po[0]-pn[0]) + abs(po[1]-pn[1]) + abs(po[2]-pn[2])
    col_diff.append(d)

# 找差异大的连续区段
segments = []
in_seg = False
start = 0
for x in range(w):
    if col_diff[x] > 2000:
        if not in_seg:
            start = x
            in_seg = True
    else:
        if in_seg:
            segments.append((start, x))
            in_seg = False
if in_seg:
    segments.append((start, w))
print("=== 任务栏差异区段（新图标）===")
for s in segments:
    if s[1] - s[0] > 15 and s[0] < 1750:
        cx = (s[0] + s[1]) // 2
        print("x {}-{} 中心x={} -> 屏幕坐标 ({},{})".format(s[0], s[1], cx, cx, 1080 - 30))
