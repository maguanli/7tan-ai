# -*- coding: utf-8 -*-
r"""裁出 y2015.png 底部 900px，供核验"""
import io, sys, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
D = r'D:\7tan\7tanAI\7723\img'
for y in ['2015', '2009']:
    im = Image.open(os.path.join(D, 'y%s.png' % y))
    W, H = im.size
    c = im.crop((0, H - 900, W, H))
    c = c.resize((940, 450))
    p = os.path.join(D, 'tail_%s.png' % y)
    c.save(p)
    print('saved', p, c.size)
