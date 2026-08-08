# -*- coding: utf-8 -*-
"""查看屏幕尺寸 + 主要窗口位置，规划微信窗口新位置"""
import ctypes, sys
from ctypes import wintypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
user32 = ctypes.windll.user32

# 屏幕尺寸
sw = user32.GetSystemMetrics(0)
sh = user32.GetSystemMetrics(1)
print(f'屏幕: {sw}x{sh}')

# 7Tan 和微信窗口位置
targets = {}
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def cb(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    if title and ('7Tan' in title or title == '微信' or 'Weixin' in title):
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if rect.right - rect.left > 100:  # 过滤小窗口
            print(f'"{title}" hwnd={hwnd} rect=({rect.left},{rect.top},{rect.right-rect.left}x{rect.bottom-rect.top}) visible={user32.IsWindowVisible(hwnd)}')
    return True

user32.EnumWindows(WNDENUMPROC(cb), 0)
print('DONE')
