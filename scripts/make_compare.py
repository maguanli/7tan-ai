# -*- coding: utf-8 -*-
"""把 side(基准) 与新生成的三张图拼成对比图，供视觉模型验证是否同一人"""
from PIL import Image, ImageDraw
import os

D = r'D:/7tan/7tanAI/镜像同事_小说/定妆图'
ref = os.path.join(D, 'character_jiangchen_side.png')
imgs = ['character_jiangchen_side.png',
        'character_jiangchen_main.png',
        'character_jiangchen_face.png',
        'character_jiangchen_full.png']

thumb_w = 400
thumbs = []
for name in imgs:
    im = Image.open(os.path.join(D, name)).convert('RGB')
    w, h = im.size
    th = int(thumb_w * h / w)
    im = im.resize((thumb_w, th), Image.LANCZOS)
    thumbs.append(im)

max_h = max(t.size[1] for t in thumbs)
canvas = Image.new('RGB', (thumb_w * len(thumbs), max_h), (20, 20, 20))
for i, t in enumerate(thumbs):
    canvas.paste(t, (i * thumb_w, (max_h - t.size[1]) // 2))

out = os.path.join(D, '_compare_jiangchen.png')
canvas.save(out, quality=92)
print('saved:', out, canvas.size)
