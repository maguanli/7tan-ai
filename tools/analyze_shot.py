# -*- coding: utf-8 -*-
"""分析成功截图 search_input.png：定位搜索框和联想面板结构"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import wechat_scan as ws

for name in ['search_input.png', 'sbhit_0.png']:
    try:
        img = Image.open(rf'D:\7tan\7tanAI\tools\ocr_work\{name}')
    except Exception as e:
        print(name, "OPEN FAIL", e)
        continue
    print(f"===== {name} size={img.size} =====")
    big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    for wx, wy, ww, wh, wt in words[:40]:
        print(f"  ({wx},{wy},{ww},{wh}) | {wt}")
