# -*- coding: utf-8 -*-
"""找发送按钮（y=795-825 蓝色像素）+ 点击输入框测试"""
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

# 确保前台
hwnd = 657662
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(0.3)

# 截图分析发送按钮
with mss.mss() as sct:
    region = {'left': 480, 'top': 200, 'width': 1060, 'height': 640}
    shot = sct.grab(region)
    to_png(shot.rgb, shot.size, output=r'data\screenshots\qq_window3.png')

img = Image.open(r'data\screenshots\qq_window3.png')
# 发送按钮区域：y 595-625 (屏幕795-825)
print('=== y=795-825 蓝色像素 ===')
blue_xs = []
for y in range(595, 626):
    for x in range(500, 900):
        r, g, b = img.getpixel((x, y))[:3]
        if b > 200 and r < 120 and g > 100:
            blue_xs.append((x, y))
if blue_xs:
    xs = [p[0] for p in blue_xs]
    ys = [p[1] for p in blue_xs]
    print(f'蓝色 x: {min(xs)}~{max(xs)} -> 屏幕 {480+min(xs)}~{480+max(xs)}')
    print(f'蓝色 y: {min(ys)}~{max(ys)} -> 屏幕 {200+min(ys)}~{200+max(ys)}')
    cx, cy = (min(xs)+max(xs))//2, (min(ys)+max(ys))//2
    print(f'按钮中心: 屏幕 ({480+cx},{200+cy})')
else:
    print('无蓝色按钮')

# 点击输入框（聊天区中央底部）并粘贴测试文字
input_x, input_y = 1100, 760
pyautogui.click(input_x, input_y)
time.sleep(0.4)
pyperclip.copy('CodeLion测试输入')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
print(f'已点击 ({input_x},{input_y}) 并粘贴')
