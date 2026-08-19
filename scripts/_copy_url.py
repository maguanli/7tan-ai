# -*- coding: utf-8 -*-
"""点击地址栏并复制 URL"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
# 点击地址栏（7Tan 浏览器地址栏在页面顶部）
pyautogui.click(500, 150)
time.sleep(0.5)
# 全选 + 复制
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'c')
time.sleep(0.5)
url = pyperclip.paste()
print("剪贴板内容:", repr(url[:500]))
