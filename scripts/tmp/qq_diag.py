# -*- coding: utf-8 -*-
import ctypes
from ctypes import wintypes
import mss
import mss.tools
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32

sw = user32.GetSystemMetrics(0)
sh = user32.GetSystemMetrics(1)
print("screen:", sw, "x", sh)

results = []
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def callback(hwnd, lparam):
    if not user32.IsWindowVisible(hwnd):
        return True
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    if title.strip():
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        minimized = user32.IsIconic(hwnd)
        results.append((int(hwnd), title, cls.value, (rect.left, rect.top, rect.right, rect.bottom), bool(minimized)))
    return True

user32.EnumWindows(EnumWindowsProc(callback), 0)
print("=== visible windows ===")
for r in results:
    print(r)

with mss.mss() as sct:
    mon = sct.monitors[0]
    img = sct.grab(mon)
    mss.tools.to_png(img.rgb, img.size, output="qq_screen_current.png")
    tb = {"left": mon["left"], "top": mon["top"] + mon["height"] - 60, "width": mon["width"], "height": 60}
    img2 = sct.grab(tb)
    mss.tools.to_png(img2.rgb, img2.size, output="taskbar.png")
print("screenshots saved")
