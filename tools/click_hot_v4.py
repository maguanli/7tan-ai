# -*- coding: utf-8 -*-
"""点击「最热」(1645,216) → 读取热门文章列表"""
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
pyautogui.click(x0 + 1645, y0 + 216)
time.sleep(3.5)
img = snap()
img.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_v4.png')
words, text = ocr_all(img)
with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_v4.txt', 'w', encoding='utf-8') as f:
    for wx, wy, ww, wh, wt in words:
        f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
    f.write("\nFULL:\n" + text)
print("标题:", [wt for wx, wy, ww, wh, wt in words if wx > 1400 and 40 < wy < 140])
print("=== 文章列表（x>1400, y>260）===")
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if wx >= 1400 and wy >= 260 and len(t) >= 6:
        print(f"  ({wx},{wy}) {t}")
