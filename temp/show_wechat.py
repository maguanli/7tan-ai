# -*- coding: utf-8 -*-
"""恢复并前置微信主窗口"""
import ctypes, sys, time
from ctypes import wintypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
HWND = 1313304  # 微信主窗口

# 恢复窗口显示
SW_RESTORE = 9
SW_SHOW = 5
user32.ShowWindow(HWND, SW_RESTORE)
time.sleep(0.3)
user32.ShowWindow(HWND, SW_SHOW)
time.sleep(0.3)

# 尝试前置
try:
    user32.SetForegroundWindow(HWND)
except Exception as e:
    print('SetForegroundWindow err:', e)
time.sleep(0.5)

# 验证状态
visible = user32.IsWindowVisible(HWND)
minimized = user32.IsIconic(HWND)
rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'visible={visible} minimized={minimized} rect=({rect.left},{rect.top},{rect.right-rect.left}x{rect.bottom-rect.top})')
print('DONE')
