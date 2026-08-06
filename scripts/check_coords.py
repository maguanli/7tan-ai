# -*- coding: utf-8 -*-
"""验证坐标系统：逻辑 vs 物理像素"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32

# 1. 当前鼠标逻辑坐标
x, y = pyautogui.position()
print(f'pyautogui.position() = ({x}, {y})')

# 2. 用 GetCursorPos 获取物理坐标
pt = wintypes.POINT()
user32.GetCursorPos(ctypes.byref(pt))
print(f'GetCursorPos = ({pt.x}, {pt.y})')

# 3. 移动鼠标到逻辑 (50, 100)
pyautogui.moveTo(50, 100)
time.sleep(0.5)
pt2 = wintypes.POINT()
user32.GetCursorPos(ctypes.byref(pt2))
print(f'after moveTo(50,100): GetCursorPos = ({pt2.x}, {pt2.y})')

# 4. 系统 DPI 缩放
try:
    dpi = user32.GetDpiForSystem()
    print(f'System DPI = {dpi} (缩放 {dpi/96:.0%})')
except Exception as e:
    print(f'GetDpiForSystem 失败: {e}')

# 5. 屏幕尺寸
print(f'pyautogui.size() = {pyautogui.size()}')
