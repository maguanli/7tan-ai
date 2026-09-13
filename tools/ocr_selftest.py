# -*- coding: utf-8 -*-
"""OCR 引擎自检：直接识别图片文件，验证引擎是否工作"""
import sys
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import region_ocr as ro

path = sys.argv[1] if len(sys.argv) > 1 else r'D:\7tan\7tanAI\tools\ocr_work\wechat_state1.png'
img = Image.open(path)
print(f"image={img.size} mode={img.mode}")

engine = ro.create_engine('windows', 'zh-CN', debug=True)
text = engine.recognize(img)
print("=== OCR TEXT ===")
print(repr(text))
print("=== END ===")
