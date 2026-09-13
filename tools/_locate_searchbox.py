# -*- coding: utf-8 -*-
"""精确定位微信搜索框：扫描 #EEEEF0 色块边界"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
from PIL import Image

WX = (351, 149, 968, 645)
with mss.mss() as sct:
    shot = sct.grab({"left": WX[0], "top": WX[1], "width": WX[2], "height": WX[3]})
img = Image.frombytes("RGB", shot.size, shot.rgb)

# 目标色
TARGET = (238, 238, 240)
# 容差
def is_target(px):
    return abs(px[0]-TARGET[0]) <= 3 and abs(px[1]-TARGET[1]) <= 3 and abs(px[2]-TARGET[2]) <= 3

w, h = img.size
# 统计每行目标色像素数和 x 范围（只看 y<160）
print("行扫描 (y, 数量, x范围):")
rows = []
for y in range(0, 160):
    cnt = 0
    xs = []
    for x in range(0, w):
        if is_target(img.getpixel((x, y))):
            cnt += 1
            if len(xs) < 2:
                xs.append(x)
    last_x = None
    for x in range(w-1, -1, -1):
        if is_target(img.getpixel((x, y))):
            last_x = x
            break
    if cnt > 5:
        rows.append((y, cnt, xs[0] if xs else -1, last_x if last_x is not None else -1))
        print(f"y={y:3d}: 数量={cnt:3d} x范围=[{xs[0] if xs else -1}, {last_x if last_x is not None else -1}]")

# 找连续的目标色行块（搜索框）
print("\n=== 连续色块分析 ===")
blocks = []
cur = []
for r in rows:
    y, cnt, x0, x1 = r
    if cur and y - cur[-1][0] > 3:  # 断行
        blocks.append(cur)
        cur = []
    cur.append(r)
if cur:
    blocks.append(cur)

for b in blocks:
    y0, y1 = b[0][0], b[-1][0]
    x0 = min(r[2] for r in b)
    x1 = max(r[3] for r in b)
    print(f"色块: y=[{y0},{y1}] 高={y1-y0+1}  x=[{x0},{x1}] 宽={x1-x0+1}  中心=({(x0+x1)//2},{(y0+y1)//2})")
