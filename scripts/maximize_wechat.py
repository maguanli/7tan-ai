# -*- coding: utf-8 -*-
"""最大化微信窗口"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
HWND = 329388

SW_MAXIMIZE = 3
user32.ShowWindow(HWND, SW_MAXIMIZE)
time.sleep(2.0)

rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'微信窗口 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom}) 尺寸 {rect.right-rect.left}x{rect.bottom-rect.top}')

# 确认前台
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: {buf.value!r}')
