# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui

# 双击草稿标题中心 (455, 555)，再单击一次卡片空白区域 (470, 500)
for x, y in [(455, 555), (470, 500)]:
    pyautogui.moveTo(x, y, duration=0.2)
    time.sleep(0.2)
    pyautogui.doubleClick(x, y)
    print(f"double-clicked ({x},{y})")
    time.sleep(1.5)
time.sleep(3)
print("done")
