# -*- coding: utf-8 -*-
"""恢复微信窗口到原始位置大小"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
HWND = 329388

SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040

# 恢复到原始位置 (50,100) 大小 766x514
user32.SetWindowPos(HWND, 0, 50, 100, 766, 514, SWP_NOZORDER | SWP_SHOWWINDOW)
time.sleep(1.5)

rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'微信窗口 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom})')
print('OK: 已恢复窗口位置')
