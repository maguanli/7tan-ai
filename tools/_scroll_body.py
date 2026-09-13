# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui

# 鼠标移到编辑区正文位置，向下滚动查看正文
pyautogui.moveTo(650, 500, duration=0.3)
time.sleep(0.3)
pyautogui.scroll(-800)  # 向下滚动
time.sleep(1.5)
pyautogui.scroll(-800)
time.sleep(1.5)
print("scrolled down")
