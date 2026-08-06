# -*- coding: utf-8 -*-
"""移动微信窗口位置并验证 mss 截图是否实时"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
HWND = 329388

# 获取当前 rect
rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'移动前 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom})')

# 移动到新位置 (600, 300)
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
user32.SetWindowPos(HWND, 0, 600, 300, 0, 0, SWP_NOZORDER | SWP_SHOWWINDOW)
time.sleep(1.5)

# 重新获取 rect
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'移动后 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom})')
print('DONE')
