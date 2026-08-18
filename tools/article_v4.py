# -*- coding: utf-8 -*-
"""双击文章tab(1650,173) → 验证切换 → 找最热"""
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

def ensure_front():
    if win32gui.GetForegroundWindow() != WX_HWND:
        win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(WX_HWND)
        time.sleep(1.0)

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

ensure_front()
pyautogui.doubleClick(x0 + 1650, y0 + 173)
time.sleep(3.5)
img = snap()
img.save(r'D:\7tan\7tanAI\tools\ocr_work\article_v3b.png')
words, text = ocr_all(img)
print("标题区:", [wt for wx, wy, ww, wh, wt in words if 1500 <= wx <= 1900 and 40 <= wy <= 130])
print("tab区:")
for wx, wy, ww, wh, wt in words:
    if wx > 1400 and 150 < wy < 260:
        print(f"  ({wx},{wy}) {wt}")
# 找最热
for wx, wy, ww, wh, wt in words:
    if '最热' in wt.replace(' ', ''):
        print(f"找到最热: ({wx},{wy}) {wt}")
