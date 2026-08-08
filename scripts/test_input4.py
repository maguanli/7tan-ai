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
# 全选删除
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.press('delete')
time.sleep(0.3)

# 粘贴明确测试文字
pyperclip.copy('TEST-123-测试')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
print('已清空并粘贴 TEST-123-测试')
