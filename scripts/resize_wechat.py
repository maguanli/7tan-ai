# -*- coding: utf-8 -*-
"""手动调整微信窗口大小"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
HWND = 329388

SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040

# 调整到 800x600 大小，位置 (400, 200)
user32.SetWindowPos(HWND, 0, 400, 200, 900, 650, SWP_NOZORDER | SWP_SHOWWINDOW)
time.sleep(2.0)

rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'微信窗口 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom}) 尺寸 {rect.right-rect.left}x{rect.bottom-rect.top}')
