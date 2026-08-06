# -*- coding: utf-8 -*-
"""关闭文件选择对话框，回到微信聊天窗口"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32
DLG_HWND = 722796

# 1. 激活对话框并按 ESC 关闭
user32.SetForegroundWindow(DLG_HWND)
time.sleep(0.5)
pyautogui.press('esc')
time.sleep(1.5)

# 2. 检查是否关闭
if user32.IsWindow(DLG_HWND):
    print('对话框仍在，尝试 Alt+F4')
    pyautogui.hotkey('alt', 'f4')
    time.sleep(1.5)

fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'当前前台窗口: {buf.value!r}')

# 3. 激活微信
user32.SetForegroundWindow(329388)
time.sleep(1.0)
print('OK: 已回到微信窗口')
