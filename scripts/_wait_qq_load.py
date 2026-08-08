# -*- coding: utf-8 -*-
"""等待 QQ 加载完成并检查窗口状态"""
import sys, io, time, ctypes
import ctypes.wintypes as wt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int
IsWindowVisible = user32.IsWindowVisible
IsWindowVisible.argtypes = [wt.HWND]
IsWindowVisible.restype = ctypes.c_bool
EnumWindows = user32.EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

print("等待 QQ 加载 8 秒...")
time.sleep(8)

windows = []
def cb(hwnd, lparam):
    if not IsWindowVisible(hwnd):
        return True
    length = GetWindowTextW(hwnd, None, 0)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if any(k in title for k in ["QQ", "7723", "腾讯"]):
            rect = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            windows.append((hwnd, title, rect.left, rect.top, rect.right, rect.bottom))
    return True

EnumWindows(WNDENUMPROC(cb), 0)
print(f"找到 {len(windows)} 个 QQ 相关窗口:")
for hwnd, title, l, t, r, b in windows:
    print(f"  hwnd={hwnd} title={title!r} rect=({l},{t},{r},{b}) w={r-l} h={b-t}")
