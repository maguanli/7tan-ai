# -*- coding: utf-8 -*-
"""诊断：前台窗口 + 当前界面 OCR + Esc 重置后重试"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

WX_HWND = 657102

def fg_info():
    h = win32gui.GetForegroundWindow()
    return h, win32gui.GetWindowText(h), win32gui.GetClassName(h)

print("FG before:", fg_info())
win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
win32gui.SetForegroundWindow(WX_HWND)
time.sleep(1.0)
print("FG after:", fg_info())

rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img):
    big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

t = ocr_all(snap())
print("STATE NOW:", t[:150])

# Esc 重置
pyautogui.press('esc')
time.sleep(1.0)
t = ocr_all(snap())
print("AFTER ESC:", t[:150])

# 点击搜索框并 write
pyautogui.click(x0+154, y0+58)
time.sleep(1.2)
print("FG at click:", fg_info())
pyautogui.write('game', interval=0.1)
time.sleep(1.2)
t = ocr_all(snap())
print("AFTER WRITE game:", t[:150])
