# -*- coding: utf-8 -*-
import time
import pyautogui
pyautogui.moveTo(700, 400)
time.sleep(0.3)
for _ in range(4):
    pyautogui.scroll(-8)
    time.sleep(0.15)
print('down')
