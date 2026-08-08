# -*- coding: utf-8 -*-
"""最小化/恢复 7Tan 主窗口"""
import ctypes, sys, time
from ctypes import wintypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
user32 = ctypes.windll.user32

HWND_7TAN = 12453212  # "7Tan — AI工具" 主窗口
HWND_WX = 1313304     # 微信

action = sys.argv[1] if len(sys.argv) > 1 else 'min'

if action == 'min':
    # 最小化 7Tan 主窗口
    user32.ShowWindow(HWND_7TAN, 6)  # SW_MINIMIZE
    time.sleep(0.5)
    # 恢复+前置微信
    user32.ShowWindow(HWND_WX, 9)  # SW_RESTORE
    time.sleep(0.2)
    try:
        user32.SetForegroundWindow(HWND_WX)
    except Exception:
        pass
    time.sleep(0.3)
    print('7Tan 已最小化，微信已前置')
elif action == 'restore':
    user32.ShowWindow(HWND_7TAN, 9)  # SW_RESTORE
    time.sleep(0.3)
    print('7Tan 已恢复')

# 验证
for name, hwnd in [('7Tan', HWND_7TAN), ('微信', HWND_WX)]:
    visible = user32.IsWindowVisible(hwnd)
    minimized = user32.IsIconic(hwnd)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    print(f'{name}: visible={visible} minimized={minimized} rect=({rect.left},{rect.top},{rect.right-rect.left}x{rect.bottom-rect.top})')
print('DONE')
