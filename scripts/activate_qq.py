# -*- coding: utf-8 -*-
"""检查前台窗口 + 强制激活 QQ"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

user32 = ctypes.windll.user32

# 检查当前前台窗口
fg = user32.GetForegroundWindow()
length = user32.GetWindowTextLengthW(fg)
buf = ctypes.create_unicode_buffer(length + 1)
user32.GetWindowTextW(fg, buf, length + 1)
print(f'当前前台窗口: hwnd={fg} title={buf.value!r}')

# 尝试多种方式激活 QQ 主窗口 657662
def activate(hwnd):
    # 方法1: SetForegroundWindow
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    if user32.GetForegroundWindow() == hwnd:
        return True
    # 方法2: ShowWindow + SetForegroundWindow
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    if user32.GetForegroundWindow() == hwnd:
        return True
    # 方法3: BringWindowToTop + SetForegroundWindow
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    return user32.GetForegroundWindow() == hwnd

ok = activate(657662)
print(f'激活结果: {ok}')
fg2 = user32.GetForegroundWindow()
length = user32.GetWindowTextLengthW(fg2)
buf = ctypes.create_unicode_buffer(length + 1)
user32.GetWindowTextW(fg2, buf, length + 1)
print(f'激活后前台窗口: hwnd={fg2} title={buf.value!r}')

if ok:
    # 点击输入框并粘贴
    pyautogui.click(1100, 740)
    time.sleep(0.6)
    pyperclip.copy('FOCUS-TEST-789')
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.8)
    print('已点击输入框并粘贴 FOCUS-TEST-789')
