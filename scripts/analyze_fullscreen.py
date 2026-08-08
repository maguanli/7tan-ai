# -*- coding: utf-8 -*-
"""全屏截图像素分析：找哪些区域有内容（深色像素），判断QQ窗口是否空白"""
import pyautogui
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 全屏截图
img = pyautogui.screenshot()
img.save(r'D:\7tan\7tanAI\scripts\fullscreen.png')
w, h = img.size
print(f"全屏: {w}x{h}")

gray = img.convert('L')
px = gray.load()

# 分析几个关键区域
regions = {
    'QQ 133662 整窗 (600,200,720x640)': (600, 200, 720, 640),
    'QQ 133662 输入框区 (604,660,616x130)': (604, 660, 616, 130),
    'QQ 3672392 整窗 (560,220,800x600)': (560, 220, 800, 600),
    'QQ 1443834 整窗 (480,200,1060x640)': (480, 200, 1060, 640),
    '桌面中部 (300,300,800x500)': (300, 300, 800, 500),
    '任务栏 (0,1030,1920x40)': (0, 1030, 1920, 40),
}

for name, (x, y, rw, rh) in regions.items():
    dark = 0
    total = 0
    for yy in range(y, min(y + rh, h), 3):
        for xx in range(x, min(x + rw, w), 3):
            total += 1
            if px[xx, yy] < 120:
                dark += 1
    ratio = dark / max(total, 1) * 100
    print(f"{name}: 深色比例 {ratio:.2f}%")
