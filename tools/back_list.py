# -*- coding: utf-8 -*-
"""返回列表 → 找所有带阅读量的文章"""
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
# 点返回（左上角）
pyautogui.click(x0 + 40, y0 + 30)
time.sleep(2.5)
img = snap()
img.save(r'D:\7tan\7tanAI\tools\ocr_work\back_to_list.png')
words, text = ocr_all(img)
print("返回后:", text[:120])

# 找「阅读」行和标题
print("=== 阅读量行 ===")
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if '阅读' in t and wy > 100:
        print(f"  ({wx},{wy}) {t}")
print("=== 文章标题（右侧 x>1400, y>250）===")
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if wx >= 1400 and wy >= 250 and len(t) >= 10:
        print(f"  ({wx},{wy}) {t}")
