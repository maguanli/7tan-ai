# -*- coding: utf-8 -*-
"""OCR 识别屏幕截图，输出文字及坐标"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

img_path = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/wechat_check_1.png'

try:
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    result, _ = ocr(img_path)
    if result:
        for box, text, score in result:
            x = int(box[0][0]); y = int(box[0][1])
            print(f'({x},{y}) {text}')
    else:
        print('NO_TEXT')
except Exception as e:
    print('ERR:', e)
