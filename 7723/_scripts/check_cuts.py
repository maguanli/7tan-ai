# -*- coding: utf-8 -*-
"""为每张年份图生成「顶部条 + 底部条」小图，供视觉核对裁剪边界"""
import os, io, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
D = r'D:\7tan\7tanAI\7723\img'
years = ['2009', '2010', '2011', '2012', '2013', '2014', '2015']
for y in years:
    p = os.path.join(D, 'year_%s.png' % y)
    im = Image.open(p)
    W, H = im.size
    strip = 300
    top = im.crop((0, 0, W, min(strip, H))).resize((W // 2, min(strip, H) // 2))
    bot = im.crop((0, max(0, H - strip), W, H)).resize((W // 2, min(strip, H) // 2))
    canvas = Image.new('RGB', (W // 2, top.size[1] + bot.size[1] + 10), 'red')
    canvas.paste(top, (0, 0))
    canvas.paste(bot, (0, top.size[1] + 10))
    out = os.path.join(D, 'check_%s.png' % y)
    canvas.save(out)
    print('check_%s.png  (top|bottom)  原图 %dx%d' % (y, W, H))
print('done')
