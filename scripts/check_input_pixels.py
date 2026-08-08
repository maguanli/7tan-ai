# -*- coding: utf-8 -*-
"""分析输入框区域是否有文字像素"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import mss
from mss.tools import to_png
from PIL import Image
import pyautogui
import pyperclip

user32 = ctypes.windll.user32
hwnd = 657662
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

def shot_input_area():
    with mss.mss() as sct:
        region = {'left': 850, 'top': 690, 'width': 490, 'height': 150}
        shot = sct.grab(region)
        to_png(shot.rgb, shot.size, output=r'data\screenshots\input_area.png')
    img = Image.open(r'data\screenshots\input_area.png')
    dark = 0
    for y in range(0, img.height, 2):
        for x in range(0, img.width, 2):
            r, g, b = img.getpixel((x, y))[:3]
            if r < 120 and g < 120 and b < 120:
                dark += 1
    print(f'输入框区域深色像素数: {dark}')
    return dark

print('=== 1. 点击输入框前 ===')
d1 = shot_input_area()

# 点击输入框
pyautogui.click(1100, 750)
time.sleep(0.5)
print('=== 2. 点击后（可能有光标）===')
d2 = shot_input_area()

# 粘贴
pyperclip.copy('CodeLion测试内容ABC')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.6)
print('=== 3. 粘贴后 ===')
d3 = shot_input_area()
print(f'深色像素: 前={d1} 点击后={d2} 粘贴后={d3}')
