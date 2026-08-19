# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

user32 = ctypes.windll.user32

# 确保窗口前台
hwnd = 657662
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# 点击输入框区域多个候选位置，观察哪里会响应
for (x, y) in [(1100, 750), (1100, 770), (1100, 790), (1000, 750), (1200, 750)]:
    pyautogui.click(x, y)
    time.sleep(0.3)
    pyperclip.copy('HELLO-TEST-2025')
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.4)
    print(f'点击 ({x},{y}) 并粘贴')
