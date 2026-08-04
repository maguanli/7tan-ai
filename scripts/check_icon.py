# -*- coding: utf-8 -*-
from PIL import Image
import os

base = r'D:\7tan\iching-android\app\src\main\res'
for d, sz in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
    p = os.path.join(base, f'mipmap-{d}', 'ic_launcher.png')
    if os.path.exists(p):
        im = Image.open(p).convert('RGB')
        colors = im.getcolors(maxcolors=1000000)
        colors.sort(reverse=True)
        top = [(c, n) for n, c in colors[:6]]
        print(d, im.size, top)
    else:
        print(d, 'MISSING')

# check adaptive icon dir
ad = os.path.join(base, 'mipmap-anydpi-v26')
print('anydpi-v26 exists:', os.path.isdir(ad))
if os.path.isdir(ad):
    print(os.listdir(ad))
