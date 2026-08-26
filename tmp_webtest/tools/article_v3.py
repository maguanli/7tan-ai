# -*- coding: utf-8 -*-
"""点文章tab(1635,173) → 找最热 → 点最热 → 读文章列表"""
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

# 1) 点「文章」tab
pyautogui.click(x0 + 1635, y0 + 173)
time.sleep(3.0)
img = snap()
words, text = ocr_all(img)
print("文章页:", text[:150])

# 2) 打印 tab/筛选行（y 150~260, x>1400）
print("=== tab区 ===")
for wx, wy, ww, wh, wt in words:
    if wx > 1400 and 150 < wy < 260:
        print(f"  ({wx},{wy}) {wt}")
