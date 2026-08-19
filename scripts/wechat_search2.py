# -*- coding: utf-8 -*-
"""点击微信搜索框并输入搜索词"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

user32 = ctypes.windll.user32
HWND = 329388

# 1. 激活窗口
user32.ShowWindow(HWND, 9)  # SW_RESTORE
time.sleep(0.5)
user32.SetForegroundWindow(HWND)
time.sleep(1.0)
print('OK: 窗口已激活')

# 2. 尝试 Ctrl+F 打开搜索（微信PC快捷键）
pyautogui.hotkey('ctrl', 'f')
time.sleep(1.5)

# 3. 输入搜索词
pyperclip.copy('7坛游戏社区')
pyautogui.hotkey('ctrl', 'v')
time.sleep(2.5)
print('OK: 已粘贴搜索词')
