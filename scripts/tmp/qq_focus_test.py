# -*- coding: utf-8 -*-
"""决定性测试：点击输入框 + Shift+Enter，对比输入框区域像素变化"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui
from PIL import Image, ImageChops

QQ_HWND = 786944

def snap(rect=(760, 770, 1370, 840)):
    import io
    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=rect)
    return img

# 激活
win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(QQ_HWND)
time.sleep(1)

# 截图1（点击前）
before = snap()
time.sleep(0.3)

# 点击输入框
pyautogui.moveTo(1000, 805, duration=0.3)
pyautogui.click()
time.sleep(1)

# 截图2（点击后，看是否有光标/聚焦变化）
after_click = snap()

# Shift+Enter 两次（换行）
pyautogui.keyDown('shift')
pyautogui.press('enter')
pyautogui.press('enter')
pyautogui.keyUp('shift')
time.sleep(1)

# 截图3（Shift+Enter后）
after_enter = snap()

# 对比差异
diff1 = ImageChops.difference(before, after_click)
diff2 = ImageChops.difference(after_click, after_enter)
bbox1 = diff1.getbbox()
bbox2 = diff2.getbbox()
print('diff click vs before bbox:', bbox1)
print('diff enter vs click bbox:', bbox2)

# 统计差异像素数
import numpy as np
a1 = np.array(diff1.convert('L'))
a2 = np.array(diff2.convert('L'))
print('changed px click:', int((a1 > 20).sum()))
print('changed px enter:', int((a2 > 20).sum()))

before.save(r'D:\7tan\7tanAI\q1_before.png')
after_click.save(r'D:\7tan\7tanAI\q2_click.png')
after_enter.save(r'D:\7tan\7tanAI\q3_enter.png')
print('saved')
