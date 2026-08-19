# -*- coding: utf-8 -*-
"""检查点击位置的实际窗口遮挡情况"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32
HWND = 329388

# 1. 微信窗口当前 rect
rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'微信窗口 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom}) 尺寸 {rect.right-rect.left}x{rect.bottom-rect.top}')
print(f'微信窗口 visible: {user32.IsWindowVisible(HWND)}')

# 2. 检查几个关键点的最上层窗口
for px, py in [(220, 270), (100, 150), (433, 357), (200, 300), (100, 100)]:
    hwnd_at = user32.WindowFromPoint(wintypes.POINT(px, py))
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd_at, buf, 256)
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd_at, cls, 256)
    print(f'点({px},{py}): 窗口 hwnd={hwnd_at} title={buf.value!r} class={cls.value!r}')

# 3. 鼠标当前位置
print('鼠标位置:', pyautogui.position())

# 4. 前台窗口
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: hwnd={fg} title={buf.value!r}')

# 5. 微信窗口 Z 序检查：是否被 7Tan 遮挡
# 枚举从微信窗口往上的所有窗口
hwnd_top = user32.GetAncestor(HWND, 2)  # GA_ROOT
print(f'微信根窗口: {hwnd_top}')
