# -*- coding: utf-8 -*-
"""对照实验：wechat_scan.ocr_words vs region_ocr 引擎 对同一图片"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import wechat_scan as ws
import region_ocr as ro

img = Image.open(r'D:\7tan\7tanAI\tools\ocr_work\wechat_state1.png')
print("img:", img.size, img.mode)

# 1) wechat_scan.ocr_words scale=1.0
try:
    words1, text1 = ws.ocr_words(img, scale=1.0)
    print(f"[ws scale=1.0] lines={len(words1)} chars={len(text1)}")
except Exception as e:
    print(f"[ws scale=1.0] ERR {type(e).__name__}: {e}")

# 2) wechat_scan.ocr_words scale=0.5
try:
    words2, text2 = ws.ocr_words(img, scale=0.5)
    print(f"[ws scale=0.5] lines={len(words2)} chars={len(text2)}")
except Exception as e:
    print(f"[ws scale=0.5] ERR {type(e).__name__}: {e}")

# 3) region_ocr 引擎
try:
    engine = ro.create_engine('windows', 'zh-CN')
    t = engine.recognize(img)
    print(f"[region_ocr] chars={len(t)}")
except Exception as e:
    print(f"[region_ocr] ERR {type(e).__name__}: {e}")

# 4) 检查引擎实例
eng = ws.get_engine()
print("[ws engine]", eng, eng.recognizer_language.language_tag if eng else None)
