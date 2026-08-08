# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

user32 = ctypes.windll.user32

# 点击输入框
pyautogui.click(1100, 750)
time.sleep(0.5)
# 多次全选删除，确保清空
for i in range(3):
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.press('delete')
    time.sleep(0.2)
print('已尝试清空输入框')
