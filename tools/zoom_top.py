# -*- coding: utf-8 -*-
"""放大窗口顶部区域 OCR，定位搜索框（微信顶部 UI 小，OCR 需放大才能识别）"""
import sys, ctypes, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import wechat_scan as ws

hwnd = 657102
import win32gui
rect = win32gui.GetWindowRect(hwnd)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0
print(f"rect={rect} size={w}x{h}")

import mss
with mss.MSS() as sct:
    shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
img = Image.frombytes('RGB', shot.size, shot.rgb)

# 顶部 160px 放大 2.5x
top_h = 160
crop = img.crop((0, 0, w, top_h))
big = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
words, text = ws.ocr_words(big, scale=1.0)
print("=== TOP AREA OCR (坐标已换算回原图) ===")
for wx, wy, ww, wh, wt in words:
    print(f"{wx//2},{wy//2},{ww//2},{wh//2} | {wt}")
print("FULL:", text[:300])
