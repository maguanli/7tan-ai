# -*- coding: utf-8 -*-
"""OCR 当前文章页，找「最热」排序位置"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
import wechat_scan as ws

WX_HWND = 1509102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

with mss.MSS() as sct:
    shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
img = Image.frombytes('RGB', shot.size, shot.rgb)
img.save(r'D:\7tan\7tanAI\tools\ocr_work\article_page_now.png')
big = img.resize((int(img.width*2), int(img.height*2)), Image.LANCZOS)
words, text = ws.ocr_words(big, scale=2.0)
with open(r'D:\7tan\7tanAI\tools\ocr_work\article_page_now.txt', 'w', encoding='utf-8') as f:
    for wx, wy, ww, wh, wt in words:
        f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
    f.write("\nFULL:\n" + text)
print("=== y 100~330, x>1400 ===")
for wx, wy, ww, wh, wt in words:
    if wx > 1400 and 100 < wy < 330:
        print(f"  ({wx},{wy},{ww},{wh}) | {wt}")
