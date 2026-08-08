# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

user32 = ctypes.windll.user32

# 点击输入框中心（聊天区下部）
input_x, input_y = 1100, 750
pyautogui.click(input_x, input_y)
time.sleep(0.8)

# 直接键入字母测试（不走剪贴板）
pyautogui.typewrite('abc', interval=0.1)
time.sleep(0.5)
print('已点击输入框并键入 abc')

# 再粘贴中文测试
pyperclip.copy('中文测试')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
print('已粘贴中文测试')
