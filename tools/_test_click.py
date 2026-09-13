# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui

# 测试点击「发表」按钮 (569,401)，观察是否有弹窗反馈
pyautogui.moveTo(569, 401, duration=0.3)
time.sleep(0.3)
pyautogui.click(569, 401)
print("clicked 发表 button (569,401)")
time.sleep(3)
print("done")
