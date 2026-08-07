# -*- coding: utf-8 -*-
"""输入 URL 到地址栏"""
import time
import pyautogui

url = "https://www.microsoft.com/en-us/wdsi/filesubmission"
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.write(url, interval=0.01)
time.sleep(0.3)
print('TYPED:', url)
