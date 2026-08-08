# -*- coding: utf-8 -*-
"""定位QQ输入框：在发送按钮左侧不同位置点击并输入'a'，截图分析'a'出现位置"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image

user32 = ctypes.windll.user32
QQ_HWND = 395876
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.5)

# 候选输入框位置（发送按钮 1272,808 左侧）
candidates = [(1000, 765), (900, 780), (1000, 790), (1100, 775), (950, 800), (800, 785)]

for i, (x, y) in enumerate(candidates):
    pyautogui.click(x, y)
    time.sleep(0.3)
    pyautogui.typewrite('a', interval=0.05)
    time.sleep(0.2)
    # 截图发送按钮左侧区域
    img = pyautogui.screenshot(region=(480, 700, 800, 140))
    img.save(rf'D:\7tan\7tanAI\scripts\qq_probe_{i}.png')
    # 分析新增深色（简化：直接看是否有'a'字样的暗区，用像素变化判断）
    print(f'候选{i}: 点击({x},{y}) 已输入a，截图 qq_probe_{i}.png')

# 最后截一张全窗口
img = pyautogui.screenshot(region=(480, 200, 1060, 640))
img.save(r'D:\7tan\7tanAI\scripts\qq_probe_full.png')
print('全窗口截图 qq_probe_full.png')
