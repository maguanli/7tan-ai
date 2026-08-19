# -*- coding: utf-8 -*-
"""滚动编辑器到顶部，截图确认布局"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
pyautogui.FAILSAFE = True

# 鼠标移到浏览器区域中心并向上滚动
pyautogui.moveTo(650, 500)
time.sleep(0.3)
for i in range(15):
    pyautogui.scroll(800)  # 向上滚动
    time.sleep(0.1)
time.sleep(1.0)
# 再按 Home 键确保到顶
pyautogui.click(650, 500)
time.sleep(0.3)
pyautogui.press('home')
time.sleep(1.0)
print("已滚动到顶部")
