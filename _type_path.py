# -*- coding: utf-8 -*-
"""pyautogui 输入正斜杠路径（避免反斜杠键在中文输入法下变顿号）"""
import time
import pyautogui

path = "D:/7tan/7tanAI/dist/release/7tan-editor-v1.0.6.zip"
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.write(path, interval=0.02)
time.sleep(0.3)
print('TYPED:', path)
