# -*- coding: utf-8 -*-
"""点击微信聊天列表中的 7坛游戏（窗口位于600,300）"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

user32 = ctypes.windll.user32
HWND = 329388

# 激活窗口
user32.SetForegroundWindow(HWND)
time.sleep(0.8)

# "7坛游戏"条目位置：窗口(600,300)，条目文字在(724,468)，点击条目中心偏右
pyautogui.moveTo(740, 480)
time.sleep(0.5)
pyautogui.click()
time.sleep(2.0)
print('OK: 已点击 (740,480)')

# 确认前台窗口
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: {buf.value!r}')
