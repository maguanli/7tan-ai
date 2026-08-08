# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32

# 激活主窗口
user32.ShowWindow(657662, 9)
user32.SetForegroundWindow(657662)
time.sleep(0.5)

# 点击 "7723手机游戏超级群" 列表项
pyautogui.click(658, 694)
time.sleep(2)
print('已点击 7723手机游戏超级群')

# 重新截图
import mss
from mss.tools import to_png
with mss.mss() as sct:
    region = {'left': 480, 'top': 200, 'width': 1060, 'height': 640}
    shot = sct.grab(region)
    to_png(shot.rgb, shot.size, output=r'data\screenshots\qq_after_click.png')
print('已保存 qq_after_click.png')
