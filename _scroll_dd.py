# -*- coding: utf-8 -*-
import time
import pyautogui
pyautogui.moveTo(500, 950)
time.sleep(0.3)
for _ in range(2):
    pyautogui.scroll(10)
    time.sleep(0.12)
print('up2')
