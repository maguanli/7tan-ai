# -*- coding: utf-8 -*-
"""激活目标群窗口 1443834，截图并定位输入框"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui

user32 = ctypes.windll.user32

TARGET_HWND = 1443834

# 激活并置顶
user32.ShowWindow(TARGET_HWND, 9)
time.sleep(0.2)
user32.SetWindowPos(TARGET_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(TARGET_HWND)
time.sleep(0.8)

rect = wt.RECT()
user32.GetWindowRect(TARGET_HWND, ctypes.byref(rect))
x, y = rect.left, rect.top
w, h = rect.right - rect.left, rect.bottom - rect.top
print(f"窗口位置: ({x},{y}) {w}x{h}")

# 全窗口截图
img = pyautogui.screenshot(region=(x, y, w, h))
img.save(r'D:\7tan\7tanAI\scripts\win_1443834_full.png')
print(f"全窗口截图 -> win_1443834_full.png")

# 底部 300px 区域（输入框所在）
img_bottom = pyautogui.screenshot(region=(x, y + h - 300, w, 300))
img_bottom.save(r'D:\7tan\7tanAI\scripts\win_1443834_bottom.png')
print(f"底部截图 -> win_1443834_bottom.png (绝对y={y+h-300})")
