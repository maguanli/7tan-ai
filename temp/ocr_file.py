# -*- coding: utf-8 -*-
"""OCR 识别图片文件（RapidOCR），验证 PrintWindow 截图内容"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'desktop_bot'))
from desktop_do import _get_rapid_engine, _ocr_garbage_ratio

img_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\7tan\7tanAI\temp\wx_printwin_test.png'

engine = _get_rapid_engine()
result, _ = engine(img_path)
lines = []
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        cx = int(sum(xs) / 4)
        cy = int(sum(ys) / 4)
        lines.append({'text': text, 'cx': cx, 'cy': cy})
print(f'识别到 {len(lines)} 行文字:')
for ln in lines[:60]:
    print(f'  ({ln["cx"]},{ln["cy"]}) {ln["text"]}')
g = _ocr_garbage_ratio(lines)
print(f'乱码率: {g:.1%}')
print('DONE')
