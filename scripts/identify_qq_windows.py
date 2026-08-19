# -*- coding: utf-8 -*-
"""依次置顶各QQ窗口，截图顶部区域用于OCR识别群名"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui

user32 = ctypes.windll.user32

hwnds = [1443834, 3672392, 133662, 460224]

for hwnd in hwnds:
    if not user32.IsWindow(hwnd):
        print(f"HWND={hwnd} 不存在，跳过")
        continue
    # 置顶
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.2)
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # HWND_TOPMOST, NOMOVE|NOSIZE|SHOWWINDOW
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    # 截取窗口顶部 300px 区域（群名所在）
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    x, y = rect.left, rect.top
    w, h = rect.right - rect.left, rect.bottom - rect.top
    top_h = min(300, h)
    img = pyautogui.screenshot(region=(x, y, w, top_h))
    out = rf'D:\7tan\7tanAI\scripts\win_{hwnd}_top.png'
    img.save(out)
    print(f"HWND={hwnd} rect=({x},{y},{w}x{h}) 顶部截图 -> {out}")
    # 恢复非置顶
    user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # HWND_NOTOPMOST
    time.sleep(0.3)
