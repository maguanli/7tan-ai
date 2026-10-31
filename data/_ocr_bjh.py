# -*- coding: utf-8 -*-
import sys, io, os
try:
    from rapidocr_onnxruntime import RapidOCR
    eng = "rapidocr_onnxruntime"
except Exception:
    try:
        from rapidocr import RapidOCR
        eng = "rapidocr"
    except Exception as e:
        sys.stdout.write("NO_RAPIDOCR %s\n" % e)
        sys.exit(0)

sys.stdout.write("ENGINE %s\n" % eng)
ocr = RapidOCR()
d = r"D:\7tan\7tanAI\data\_bjh_img"
lines = []
for n in ["04", "05", "12", "13", "14"]:
    p = os.path.join(d, n + ".jpg")
    if not os.path.exists(p):
        continue
    res, _ = ocr(p)
    lines.append("===== %s.jpg =====" % n)
    if not res:
        lines.append("(no text)")
        continue
    for item in res:
        try:
            box, txt, sc = item[0], item[1], item[2]
            y = int(sum(pt[1] for pt in box) / 4)
            x = int(sum(pt[0] for pt in box) / 4)
            lines.append("(%d,%d) %s" % (x, y, txt))
        except Exception:
            lines.append(str(item))
io.open(r"D:\7tan\7tanAI\data\_bjh_ocr.txt", "w", encoding="utf-8").write("\n".join(lines))
sys.stdout.write("DONE %d lines\n" % len(lines))
