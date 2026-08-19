# -*- coding: utf-8 -*-
"""检查所有 QQ 窗口当前状态"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

results = []
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def callback(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if pid.value in (6272, 6468, 1708, 12996, 8188, 13572, 11708, 448):
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            visible = user32.IsWindowVisible(hwnd)
            results.append((hwnd, title, visible, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
    return True

user32.EnumWindows(EnumWindowsProc(callback), 0)

print('=== QQ 窗口当前状态 ===')
for hwnd, title, visible, l, t, w, h in results:
    print(f'hwnd={hwnd} title={title!r} visible={visible} pos=({l},{t}) size={w}x{h}')
