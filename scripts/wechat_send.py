# -*- coding: utf-8 -*-
"""按回车发送问候消息"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

pyautogui.FAILSAFE = True

user32 = ctypes.windll.user32
HWND = 329388

# 确保微信前台
user32.SetForegroundWindow(HWND)
time.sleep(0.8)

# 按回车发送
pyautogui.press('enter')
time.sleep(2.5)
print('OK: 已按回车发送')

fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: {buf.value!r}')
