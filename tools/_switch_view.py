# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui

for name, x, y in [("AI工作台", 58, 153), ("浏览器标签", 350, 45)]:
    pyautogui.moveTo(x, y, duration=0.3)
    time.sleep(0.2)
    pyautogui.click(x, y)
    print(f"clicked {name} ({x},{y})")
    time.sleep(1.5)
print("done")
