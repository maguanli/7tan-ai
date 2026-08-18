# -*- coding: utf-8 -*-
"""完整 OCR 当前微信界面（全窗口），输出 words 坐标到 UTF-8 文件"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
import wechat_scan as ws

WX_HWND = 657102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

with mss.MSS() as sct:
    shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
img = Image.frombytes('RGB', shot.size, shot.rgb)
img.save(r'D:\7tan\7tanAI\tools\ocr_work\search_page.png')

big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
words, text = ws.ocr_words(big, scale=1.0)

with open(r'D:\7tan\7tanAI\tools\ocr_work\search_page.txt', 'w', encoding='utf-8') as f:
    f.write("=== WORDS (abs=窗口内坐标) ===\n")
    for wx, wy, ww, wh, wt in words:
        f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
    f.write("\n=== FULL ===\n" + text.replace(' ', ''))
print(f"LINES={len(words)} saved search_page.txt")
print("PREVIEW:")
for wx, wy, ww, wh, wt in words[:45]:
    print(f"  ({wx},{wy},{ww},{wh}) | {wt}")
