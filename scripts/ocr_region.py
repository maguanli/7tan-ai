# -*- coding: utf-8 -*-
"""裁剪指定区域并OCR"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

src = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/wechat_after_click.png'
# region: left, top, right, bottom
region = [int(v) for v in sys.argv[2].split(',')] if len(sys.argv) > 2 else [200, 0, 700, 700]
tmp = 'data/screenshots/_region_tmp.png'

img = Image.open(src).convert('RGB')
crop = img.crop(region)
print('region:', region, 'crop size:', crop.size)
crop.save(tmp)

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
result, _ = ocr(tmp)
if result:
    for box, text, score in result:
        x = int(box[0][0]) + region[0]
        y = int(box[0][1]) + region[1]
        print(f'({x},{y}) {text}')
else:
    print('NO_TEXT')
