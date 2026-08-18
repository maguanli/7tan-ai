# -*- coding: utf-8 -*-
"""诊断前台 + 双击搜一搜入口重试"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

WX_HWND = 1509102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

fg = win32gui.GetForegroundWindow()
print("FG:", fg, "is_wx:", fg == WX_HWND)
if fg != WX_HWND:
    win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
    win32gui.SetForegroundWindow(WX_HWND)
    time.sleep(1.0)
    print("after FG:", win32gui.GetForegroundWindow())

# 双击搜索入口
pyautogui.doubleClick(x0 + 80, y0 + 179)
time.sleep(3.0)
img = snap()
words, text = ocr_all(img)
print("双击后:", text[:150])
# 右侧是否有搜一搜内容
right = [wt for wx, wy, ww, wh, wt in words if wx > 1400 and wy > 40]
print("右侧words:", right[:15])
