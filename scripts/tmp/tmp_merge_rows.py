# -*- coding: utf-8 -*-
"""拼接行截图成3张大图，每张带行号标签"""
from PIL import Image, ImageDraw
import os

src = r"D:\7tan\7tanAI\data\screenshots\rows"
out = r"D:\7tan\7tanAI\data\screenshots"

groups = [list(range(0, 5)), list(range(5, 9)), list(range(9, 13))]
for gi, g in enumerate(groups):
    imgs = []
    for i in g:
        f = [x for x in os.listdir(src) if x.startswith(f"row_{i:02d}_")]
        if not f:
            continue
        im = Image.open(os.path.join(src, f[0]))
        # 加标签
        canvas = Image.new("RGB", (im.width, im.height + 40), (255, 0, 0))
        canvas.paste(im, (0, 40))
        d = ImageDraw.Draw(canvas)
        d.text((10, 8), f"ROW {i} (screen y {140+i*54}-{min(140+i*54+54,860)})", fill=(0, 0, 0))
        imgs.append(canvas)
    if imgs:
        total_h = sum(im.height for im in imgs)
        wmax = max(im.width for im in imgs)
        canvas = Image.new("RGB", (wmax, total_h), (255, 255, 255))
        y = 0
        for im in imgs:
            canvas.paste(im, (0, y))
            y += im.height
        canvas.save(os.path.join(out, f"rows_group_{gi}.png"))
        print(f"group_{gi}: {len(imgs)} rows, {canvas.size}")
