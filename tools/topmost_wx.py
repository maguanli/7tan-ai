# -*- coding: utf-8 -*-
"""把微信窗口置顶(TOPMOST) → 恢复前台 → 返回搜索页"""
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
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def ensure_front():
    if win32gui.GetForegroundWindow() != WX_HWND:
        win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(WX_HWND)
        time.sleep(1.2)
    return win32gui.GetForegroundWindow() == WX_HWND

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

# 置顶微信窗口
win32gui.SetWindowPos(WX_HWND, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                       win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
time.sleep(0.5)
print("TOPMOST set, foreground:", ensure_front())

# 点返回（左上角）
pyautogui.click(x0 + 50, y0 + 28)
time.sleep(2.0)
img = snap()
words, text = ocr_all(img)
print("返回后:", text[:150])

# 保存当前状态
img.save(r'D:\7tan\7tanAI\tools\ocr_work\after_back.png')
with open(r'D:\7tan\7tanAI\tools\ocr_work\after_back.txt', 'w', encoding='utf-8') as f:
    for wx, wy, ww, wh, wt in words:
        f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
    f.write("\nFULL:\n" + text)
