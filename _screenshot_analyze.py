# -*- coding: utf-8 -*-
"""截取当前屏幕，分析左上角侧边栏区域的颜色特征，判断显示的是哪个图标"""
import sys
from PIL import ImageGrab

im = ImageGrab.grab()
im.save(r"D:\7tan\7tanAI\_screen_now.png")
W, H = im.size
print("screen:", W, H)

# 分析窗口可能位置：左上角 250x120 区域（侧边栏顶部 logo 区域）
regions = {
    "A(0-100,0-80)": (0, 0, 100, 80),
    "B(0-200,0-60)": (0, 0, 200, 60),
    "C(0-80,0-160)": (0, 0, 80, 160),
}
for name, box in regions.items():
    crop = im.crop(box).convert("RGB")
    px = list(crop.getdata())
    n = len(px)
    # 统计颜色类别（量化）
    from collections import Counter
    cnt = Counter()
    for r, g, b in px:
        cnt[(r // 32 * 32, g // 32 * 32, b // 32 * 32)] += 1
    top = cnt.most_common(8)
    total = sum(c for _, c in top)
    print(f"\n[{name}] 采样{n}px")
    for c, count in top:
        print(f"  RGB~{c}  {count/n*100:.1f}%")
