# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32

# 先把 QQ 主窗口置前
hwnd = 657662
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# 点击 "7723手机游戏超级群" 群列表项（中心约 x=658, y=694）
x, y = 658, 694
pyautogui.moveTo(x, y, duration=0.3)
time.sleep(0.2)
pyautogui.click(x, y)
print(f'已点击群列表项 ({x},{y})')
time.sleep(2)

# 点击后截图 OCR 验证窗口
print('等待聊天窗口加载...')
time.sleep(1.5)
