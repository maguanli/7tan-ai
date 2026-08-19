# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui

# 1. Esc 关闭可能打开的发表面板
pyautogui.press("esc")
time.sleep(1)
print("pressed esc")

# 2. 鼠标移到编辑区正文，滚动到底部
pyautogui.moveTo(650, 500, duration=0.3)
time.sleep(0.3)
for _ in range(6):
    pyautogui.scroll(-600)
    time.sleep(0.8)
print("scrolled to bottom")
