# -*- coding: utf-8 -*-
"""检查当前前台窗口和微信窗口状态"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# 前台窗口
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
cls = ctypes.create_unicode_buffer(256)
user32.GetClassNameW(fg, cls, 256)
print(f'前台窗口: hwnd={fg} title={buf.value!r} class={cls.value!r}')

# 微信窗口状态
rect = wintypes.RECT()
user32.GetWindowRect(329388, ctypes.byref(rect))
print(f'微信窗口 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom})')

# 枚举所有可见窗口
results = []
@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            b = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, b, length + 1)
            results.append((hwnd, b.value))
    return True
user32.EnumWindows(cb, 0)
for h, t in results:
    print(f'  hwnd={h} {t!r}')
