# -*- coding: utf-8 -*-
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
import mss
import mss.tools

# 1. 真实光标移动到开始按钮并点击
print("点击开始按钮...")
pyautogui.moveTo(20, 1065, duration=0.6)
time.sleep(0.2)
pyautogui.click()
time.sleep(1.2)

# 2. 截图确认开始菜单
with mss.mss() as sct:
    mon = sct.monitors[1]
    img = sct.grab(mon)
    mss.tools.to_png(img.rgb, img.size, output="startmenu.png")
print("startmenu.png saved")

# 3. 在开始菜单搜索框输入 qq（真实键盘）
print("输入 qq...")
pyautogui.typewrite("qq", interval=0.15)
time.sleep(2.0)

# 4. 截图搜索结果
with mss.mss() as sct:
    mon = sct.monitors[1]
    img = sct.grab(mon)
    mss.tools.to_png(img.rgb, img.size, output="search_result.png")
print("search_result.png saved")
