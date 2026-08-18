# -*- coding: utf-8 -*-
"""截图并 OCR 指定屏幕区域"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import mss, wechat_scan as ws

x, y, x2, y2 = 551, 208, 715, 372
w, h = x2-x, y2-y
with mss.MSS() as sct:
    shot = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
img = Image.frombytes('RGB', shot.size, shot.rgb)
img.save(r'D:\7tan\7tanAI\tools\ocr_work\popup.png')
big = img.resize((img.width*3, img.height*3), Image.LANCZOS)
words, text = ws.ocr_words(big, scale=1.0)
print("=== POPUP AREA OCR (坐标=原始) ===")
for wx, wy, ww, wh, wt in words:
    print(f"{wx//3+x},{wy//3+y},{ww//3},{wh//3} | {wt}")
print("FULL:", text[:300])
