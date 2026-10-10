# -*- coding: utf-8 -*-
from PIL import Image

im = Image.open(r"D:\7tan\7tanAI\data\screenshots\_sohu_look.png").convert("RGB")
W, H = im.size
px = im.load()
x0, x1 = 45, 940
step = 2
n = len(range(x0, x1, step))
print("size", W, H, "cols", n)

rows = []
for y in range(H):
    ink = ph = wh = 0
    for x in range(x0, x1, step):
        r, g, b = px[x, y]
        mx, mn = max(r, g, b), min(r, g, b)
        if mn > 245:
            wh += 1
        if mn < 180:
            ink += 1
        if (mx - mn) > 35 and 40 < mx < 235:
            ph += 1
    rows.append((y, ink / n, ph / n, wh / n))

print("\n--- 每 25 行汇总 (avg photo / avg ink / avg white) ---")
for y0 in range(0, H - 25, 25):
    seg = rows[y0:y0 + 25]
    ap = sum(s[2] for s in seg) / len(seg)
    ai = sum(s[1] for s in seg) / len(seg)
    aw = sum(s[3] for s in seg) / len(seg)
    tag = "PHOTO" if ap > 0.12 else ("TEXT" if ai > 0.01 else "blank")
    print("  y=%4d-%4d  photo=%.2f ink=%.2f white=%.2f  %s" % (y0, y0 + 24, ap, ai, aw, tag))

print("\n--- 连续 PHOTO 行区间(photo>0.12) ---")
cur = None
for y, ink, ph, wh in rows:
    if ph > 0.12:
        if cur is None:
            cur = [y, y]
        else:
            cur[1] = y
    else:
        if cur and cur[1] - cur[0] > 10:
            print("   PHOTO %d..%d (h=%d)" % (cur[0], cur[1], cur[1] - cur[0] + 1))
        cur = None
if cur and cur[1] - cur[0] > 10:
    print("   PHOTO %d..%d (h=%d)" % (cur[0], cur[1], cur[1] - cur[0] + 1))
