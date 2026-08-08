# -*- coding: utf-8 -*-
import json, io
from rapidocr_onnxruntime import RapidOCR
engine = RapidOCR()
result, _ = engine(r"D:\7tan\7tanAI\tmp_wechat_screen.png")
lines = []
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        lines.append({"text": text, "x": int(min(xs)), "y": int(min(ys)),
                      "w": int(max(xs)-min(xs)), "h": int(max(ys)-min(ys)), "score": round(float(score), 3)})
out = io.open(r"D:\7tan\7tanAI\tmp_ocr_result.json", "w", encoding="utf-8")
json.dump(lines, out, ensure_ascii=False, indent=1)
out.close()
print("OCR_OK", len(lines))
