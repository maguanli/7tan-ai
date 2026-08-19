# -*- coding: utf-8 -*-
"""输入 Company Name（聚焦后先清空再输入）"""
import time
import pyautogui
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.write("Individual", interval=0.05)
time.sleep(0.3)
print('TYPED Individual')
