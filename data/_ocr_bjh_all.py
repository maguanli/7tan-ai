# -*- coding: utf-8 -*-
import sys, io, os
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
d = r"D:\7tan\7tanAI\data\_bjh_img"
lines = []
for n in ["%02d" % i for i in range(1, 15)]:
    p = os.path.join(d, n + ".jpg")
    if not os.path.exists(p):
        continue
    res, _ = ocr(p)
    lines.append("===== %s.jpg =====" % n)
    if not res:
        lines.append("(no text)")
        continue
    for item in res:
        box, txt = item[0], item[1]
        y = int(sum(pt[1] for pt in box) / 4)
        lines.append("y%d %s" % (y, txt))
io.open(r"D:\7tan\7tanAI\data\_bjh_ocr_all.txt", "w", encoding="utf-8").write("\n".join(lines))
sys.stdout.write("DONE %d\n" % len(lines))
