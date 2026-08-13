# -*- coding: utf-8 -*-
"""列出所有可见窗口"""
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
            results.append((hwnd, buf.value))
    return True

user32.EnumWindows(enum_cb, 0)
for hwnd, title in results:
    print(f'{hwnd}: {title}')
