# -*- coding: utf-8 -*-
"""显示并激活微信主窗口"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

HWND = 329388
SW_SHOW = 5
SW_RESTORE = 9

# 显示窗口
user32.ShowWindow(HWND, SW_SHOW)
user32.ShowWindow(HWND, SW_RESTORE)
time.sleep(0.5)

# 移到前台
user32.SetForegroundWindow(HWND)
time.sleep(0.5)

# 获取窗口矩形
rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'Window rect: left={rect.left} top={rect.top} right={rect.right} bottom={rect.bottom}')
print(f'Size: {rect.right - rect.left} x {rect.bottom - rect.top}')
print('visible after:', user32.IsWindowVisible(HWND))
print('DONE')
