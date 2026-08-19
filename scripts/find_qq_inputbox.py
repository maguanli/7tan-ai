# -*- coding: utf-8 -*-
"""精确定位QQ输入框：分析窗口底部的白色矩形区域"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image
import numpy as np

user32 = ctypes.windll.user32
QQ_HWND = 1443834

# 确保窗口在顶部
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.5)

# 截取窗口底部区域 (窗口 y 200~840, 底部 400px: y 440~840)
img = pyautogui.screenshot(region=(480, 440, 1060, 400))
img.save(r'D:\7tan\7tanAI\scripts\qq_bottom_area.png')
arr = np.array(img.convert('RGB')).astype(int)
h, w, _ = arr.shape
print(f'底部区域: {w}x{h} (绝对坐标 y=440~840)')

# 白色像素判定（输入框底色：接近纯白）
white = (arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235)
row_white = white.sum(axis=1)

print('\n=== 白色行分布（每10行） ===')
for y in range(0, h, 10):
    seg = row_white[y:y+10].mean()
    print(f'  abs_y={440+y:4d}: 白色均值 {seg:6.1f}')

# 找连续白色带（输入框）：白色像素 > 宽度的 30%
print('\n=== 连续白色带（输入框候选） ===')
in_band = False
band_start = 0
for y in range(h):
    is_white_row = row_white[y] > w * 0.3
    if is_white_row and not in_band:
        in_band = True
        band_start = y
    elif not is_white_row and in_band:
        in_band = False
        if y - band_start > 20:
            print(f'  白色带: abs_y={440+band_start} ~ {440+y} (高{y-band_start}px)')
if in_band:
    print(f'  白色带(末尾): abs_y={440+band_start} ~ {440+h}')
