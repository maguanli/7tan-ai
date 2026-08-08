# -*- coding: utf-8 -*-
"""压缩图片后 OCR，加速识别"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

src = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/desktop_full.png'
max_w = int(sys.argv[2]) if len(sys.argv) > 2 else 1280
tmp = 'data/screenshots/_ocr_tmp.png'

img = Image.open(src).convert('RGB')
if img.width > max_w:
    h = int(img.height * max_w / img.width)
    img = img.resize((max_w, h), Image.LANCZOS)
img.save(tmp, quality=90)
print('resized:', img.size)

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
result, _ = ocr(tmp)
if result:
    for box, text, score in result:
        x = int(box[0][0]); y = int(box[0][1])
        scale = img.width / max_w
        print(f'({int(x*scale)},{int(y*scale)}) {text}')
else:
    print('NO_TEXT')
