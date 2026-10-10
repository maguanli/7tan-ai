# -*- coding: utf-8 -*-
r"""核验：把 y20xx.png 的顶部条 + 底部条 拼成两张对照图"""
import os, io, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
D = r'D:\7tan\7tanAI\7723\img'
years = ['2009', '2010', '2011', '2012', '2013', '2014', '2015']

def build(kind, outname):
    strips = []
    for y in years:
        im = Image.open(os.path.join(D, 'y%s.png' % y))
        W, H = im.size
        s = 200
        if kind == 'top':
            c = im.crop((0, 0, W, s))
        else:
            c = im.crop((0, max(0, H - s), W, H))
        c = c.resize((760, int(c.size[1] * 760 / c.size[0])))
        strips.append((y, c))
    total_h = sum(c.size[1] for _, c in strips) + 6 * len(strips)
    canvas = Image.new('RGB', (760, total_h), (255, 0, 0))
    yy = 0
    for y, c in strips:
        canvas.paste(c, (0, yy))
        yy += c.size[1] + 6
    p = os.path.join(D, outname)
    canvas.save(p)
    print('saved', p, canvas.size)

build('top', 'STACK_top.png')
build('bot', 'STACK_bot.png')
print('done')
