# -*- coding: utf-8 -*-
"""检查 QQ 各窗口的 z-order、可见性、位置"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# 枚举窗口，按 z-order（EnumWindows 按 z-order 从上到下）
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
            # 检查是否在桌面上层（GetWindow 前一个窗口）
            results.append((hwnd, title, visible, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
    return True

user32.EnumWindows(EnumWindowsProc(callback), 0)

print('=== QQ 窗口 (按 z-order 从上到下) ===')
for i, (hwnd, title, visible, l, t, w, h) in enumerate(results):
    print(f'{i}: hwnd={hwnd} title={title!r} visible={visible} pos=({l},{t}) size={w}x{h}')
