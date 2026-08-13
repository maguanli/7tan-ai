# -*- coding: utf-8 -*-
"""最小化 7Tan 窗口，让 Chrome 露出"""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

results = []

@ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def enum_cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if '7Tan' in title:
                results.append((hwnd, title))
    return True

user32.EnumWindows(enum_cb, 0)

for hwnd, title in results:
    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    print(f'minimized: {title} hwnd={hwnd}')

if not results:
    print('no 7Tan window found')
