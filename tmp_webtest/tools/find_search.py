# -*- coding: utf-8 -*-
"""关闭弹窗 + 3x放大OCR窗口顶部，找搜索框"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.2

hwnd = 657102
rect = win32gui.GetWindowRect(hwnd)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

# 1) 点击菜单外区域关闭（窗口内 0.85, 0.18 空白处）
pyautogui.click(x0 + int(w*0.85), y0 + int(h*0.18))
time.sleep(1.0)

# 2) 截图顶部放大3倍 OCR
with mss.MSS() as sct:
    shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
img = Image.frombytes('RGB', shot.size, shot.rgb)
img.save(r'D:\7tan\7tanAI\tools\ocr_work\full1.png')

for top_h in (140, 220):
    crop = img.crop((0, 0, w, top_h))
    for zoom in (3,):
        big = crop.resize((crop.width*zoom, crop.height*zoom), Image.LANCZOS)
        words, text = ws.ocr_words(big, scale=1.0)
        print(f"=== TOP {top_h}px zoom{zoom} ===")
        for wx, wy, ww, wh, wt in words:
            print(f"  {wx//zoom},{wy//zoom},{ww//zoom},{wh//zoom} | {wt}")
        print("  FULL:", text.replace(' ', '')[:200])
