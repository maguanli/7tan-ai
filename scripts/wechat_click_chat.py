# -*- coding: utf-8 -*-
"""点击微信聊天列表中的 7坛游戏 条目"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

user32 = ctypes.windll.user32
HWND = 329388

# 1. 激活微信窗口
user32.ShowWindow(HWND, 9)
time.sleep(0.3)
user32.SetForegroundWindow(HWND)
time.sleep(0.8)

# 2. 点击"7坛游戏"条目（聊天列表第2项）
# OCR定位文字在 (176,263)，条目区域约 (105,240)-(350,300)，点击中心 (220, 270)
pyautogui.click(220, 270)
time.sleep(2.0)
print('OK: 已点击 7坛游戏 条目')

# 3. 检查前台窗口是否还是微信
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: {buf.value!r}')
