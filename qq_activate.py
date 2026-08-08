# -*- coding: utf-8 -*-
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
import mss
import mss.tools
import ctypes
from ctypes import wintypes

# 1. 真实光标点击任务栏 QQ 图标
print("点击任务栏 QQ 图标 (878,1050)...")
pyautogui.moveTo(878, 1050, duration=0.8)
time.sleep(0.3)
pyautogui.click()
time.sleep(1.5)

# 2. 检查前台窗口
user32 = ctypes.windll.user32
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print("前台窗口 hwnd={} title={!r}".format(fg, buf.value))

# 3. 截图确认
with mss.mss() as sct:
    mon = sct.monitors[1]
    img = sct.grab(mon)
    mss.tools.to_png(img.rgb, img.size, output="qq_activated.png")
print("qq_activated.png saved")
