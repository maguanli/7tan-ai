# -*- coding: utf-8 -*-
"""全屏截图 + easyocr 定位「论四十岁」草稿卡片坐标"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image
import numpy as np

KEYWORD = "论四十岁"

# 1. 全屏截图
with mss.mss() as sct:
    shot = sct.grab(sct.monitors[1])  # 主屏
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\_fullscreen.png")
print(f"全屏截图: {img.size}, 缩放50%加速识别...")

# 2. 缩小识别（加速）
small = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
arr = np.array(small)

# 3. easyocr 识别
import easyocr
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
results = reader.readtext(arr)

found = []
for bbox, text, conf in results:
    xs = [p[0] for p in bbox]; ys = [p[1] for p in bbox]
    cx, cy = sum(xs)/4, sum(ys)/4
    # 放大回原坐标
    ox, oy = cx*2, cy*2
    if KEYWORD in text.replace(' ', ''):
        found.append((text, int(ox), int(oy), float(conf)))
    else:
        pass

print("=== 包含关键词的结果 ===")
if found:
    for t, x, y, c in found:
        print(f"text={t!r} x={x} y={y} conf={c:.2f}")
else:
    print("未找到关键词，输出全部识别文本(前40条):")
    for bbox, text, conf in results[:40]:
        xs = [p[0] for p in bbox]; ys = [p[1] for p in bbox]
        print(f"  [{int(sum(xs)/4*2)},{int(sum(ys)/4*2)}] {text!r} ({conf:.2f})")
