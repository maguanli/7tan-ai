# -*- coding: utf-8 -*-
"""定位文章页「最热」精确坐标（打印筛选行所有 words）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import wechat_scan as ws

img = Image.open(r'D:\7tan\7tanAI\tools\ocr_work\article_now.png')
big = img.resize((int(img.width*2), int(img.height*2)), Image.LANCZOS)
words, text = ws.ocr_words(big, scale=2.0)
print("=== 筛选行区域 (x 520~900, y 150~240) ===")
for wx, wy, ww, wh, wt in words:
    if 520 <= wx <= 900 and 150 <= wy <= 240:
        print(f"  ({wx},{wy},{ww},{wh}) | {wt!r}")
print()
print("=== 包含 最/热/新 的词 ===")
for wx, wy, ww, wh, wt in words:
    if any(c in wt for c in '最热新'):
        print(f"  ({wx},{wy},{ww},{wh}) | {wt!r}")
