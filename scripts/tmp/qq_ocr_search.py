# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from cnocr import CnOcr

print("加载 cnocr 模型（首次可能较慢）...")
ocr = CnOcr()
print("模型加载完成，开始识别 search_result.png ...")
res = ocr.ocr("search_result.png")
print("=== 识别结果 ===")
for item in res:
    text = item.get('text', '')
    pos = item.get('position', [])
    score = item.get('score', 0)
    if pos:
        xs = [p[0] for p in pos]
        ys = [p[1] for p in pos]
        cx = int(sum(xs) / len(xs))
        cy = int(sum(ys) / len(ys))
    else:
        cx, cy = -1, -1
    print("text={!r} score={:.2f} center=({},{})".format(text, score, cx, cy))
