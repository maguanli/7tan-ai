# -*- coding: utf-8 -*-
"""最大化微信窗口 + 置顶 + 截图 OCR"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

WX_HWND = 1509102

# 最大化 + 置顶
win32gui.ShowWindow(WX_HWND, win32con.SW_MAXIMIZE)
time.sleep(0.8)
win32gui.SetWindowPos(WX_HWND, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                       win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
win32gui.SetForegroundWindow(WX_HWND)
time.sleep(1.2)

rect = win32gui.GetWindowRect(WX_HWND)
print("rect:", rect)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

with mss.MSS() as sct:
    shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
img = Image.frombytes('RGB', shot.size, shot.rgb)
img.save(r'D:\7tan\7tanAI\tools\ocr_work\max_wx.png')
big = img.resize((int(img.width*2), int(img.height*2)), Image.LANCZOS)
words, text = ws.ocr_words(big, scale=2.0)
with open(r'D:\7tan\7tanAI\tools\ocr_work\max_wx.txt', 'w', encoding='utf-8') as f:
    for wx, wy, ww, wh, wt in words:
        f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
    f.write("\nFULL:\n" + text)
print("=== 最大化后界面 ===")
print(text[:200])
# 打印左上角区域 words（找搜索入口）
print("=== 左上角区域 (x<300, y<250) ===")
for wx, wy, ww, wh, wt in words:
    if wx < 300 and wy < 250:
        print(f"  ({wx},{wy},{ww},{wh}) | {wt}")
