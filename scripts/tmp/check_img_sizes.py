# -*- coding: utf-8 -*-
from PIL import Image
import os

d = 'downloads/marriage_article'
for f in sorted(os.listdir(d)):
    if f.endswith(('.jpg', '.png')):
        p = os.path.join(d, f)
        try:
            im = Image.open(p)
            print(f'{f}: {im.size[0]}x{im.size[1]}, {os.path.getsize(p)//1024}KB, mode={im.mode}')
        except Exception as e:
            print(f'{f}: ERROR {e}')
