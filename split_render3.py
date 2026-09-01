# -*- coding: utf-8 -*-
from PIL import Image
import os

src = r"D:\7tan\7tanAI\downloads\poxi_article\render_check3.png"
img = Image.open(src)
w, h = img.size
print("size:", w, h)

outdir = r"D:\7tan\7tanAI\downloads\poxi_article"
n = 3
step = h // n
for i in range(n):
    top = i * step
    bottom = h if i == n - 1 else (i + 1) * step
    seg = img.crop((0, top, w, bottom))
    p = os.path.join(outdir, "seg%d.png" % (i + 1))
    seg.save(p)
    print("saved", p, seg.size)
