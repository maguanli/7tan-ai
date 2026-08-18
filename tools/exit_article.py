# -*- coding: utf-8 -*-
"""退出文章页：Esc → 点× → 验证 → 重开搜一搜"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
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

# Esc
pyautogui.press('esc')
time.sleep(2.0)
img = snap()
words, text = ocr_all(img)
right = [wt for wx, wy, ww, wh, wt in words if wx > 1400 and wy > 40]
print("Esc后右侧:", right[:10])
print("Esc后:", text[:100])

# 点右上角 × (x0+1856, y0+19) — 窗口右上角
pyautogui.click(x0 + 1856, y0 + 19)
time.sleep(2.0)
img = snap()
words, text = ocr_all(img)
right = [wt for wx, wy, ww, wh, wt in words if wx > 1400 and wy > 40]
print("点×后右侧:", right[:10])
print("点×后:", text[:100])
