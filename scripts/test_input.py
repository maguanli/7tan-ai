# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

user32 = ctypes.windll.user32

# 确保 QQ 主窗口在前台
hwnd = 657662
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# 1. 点击聊天记录区空白处聚焦窗口
pyautogui.click(1150, 700)
time.sleep(0.3)

# 2. 点击聊天窗口底部输入框区域（聊天区底部中央）
input_x, input_y = 1150, 820
pyautogui.click(input_x, input_y)
time.sleep(0.5)

# 3. 粘贴测试文字
pyperclip.copy('CodeLion测试输入')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)

print(f'已点击输入框 ({input_x},{input_y}) 并粘贴测试文字')
