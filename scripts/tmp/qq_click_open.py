# -*- coding: utf-8 -*-
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
import mss
import mss.tools
import ctypes
from ctypes import wintypes

# 1. 真实光标点击 QQ 应用项 (116, 505)
print("移动光标到 QQ 应用项 (116,505)...")
pyautogui.moveTo(116, 505, duration=0.8)
time.sleep(0.3)
pyautogui.click()
print("已点击！等待 QQ 启动...")
time.sleep(6)

# 2. 截图确认
with mss.mss() as sct:
    mon = sct.monitors[1]
    img = sct.grab(mon)
    mss.tools.to_png(img.rgb, img.size, output="qq_opened.png")
print("qq_opened.png saved")

# 3. 枚举窗口找 QQ
user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
found = []
def cb(hwnd, lparam):
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
        found.append((int(hwnd), title, cls.value, (rect.left, rect.top, rect.right, rect.bottom), bool(user32.IsIconic(hwnd))))
    return True
user32.EnumWindows(EnumWindowsProc(cb), 0)
print("=== 当前可见窗口 ===")
for f in found:
    print(f)
