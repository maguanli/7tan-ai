# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui

print("pos before:", pyautogui.position())
pyautogui.moveTo(34, 194, duration=0.5)
print("pos after move:", pyautogui.position())
time.sleep(0.3)
pyautogui.click()
print("clicked (34,194), pos:", pyautogui.position())
time.sleep(2)
print("done")
