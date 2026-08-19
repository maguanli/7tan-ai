# -*- coding: utf-8 -*-
"""双击微信聊天列表中的 7坛游戏 条目"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2

user32 = ctypes.windll.user32
HWND = 329388

user32.SetForegroundWindow(HWND)
time.sleep(0.8)

# 双击 7坛游戏 条目 (785, 480)
pyautogui.moveTo(785, 480)
time.sleep(0.4)
pyautogui.doubleClick()
time.sleep(2.5)
print('OK: 已双击 (785,480)')

fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: {buf.value!r}')
