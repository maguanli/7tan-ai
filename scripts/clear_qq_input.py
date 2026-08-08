# -*- coding: utf-8 -*-
"""清除输入框测试文字"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
import time

# 点击输入框
pyautogui.click(1050, 850)
time.sleep(0.5)
# 全选 + 删除
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.press('delete')
time.sleep(0.5)
print('测试文字已清除')
print('DONE')
