# -*- coding: utf-8 -*-
from PIL import Image, ImageStat
import os

for p in ['downloads/covers/deepseek_v4_flash_0731_cover.png',
          'downloads/covers/deepseek_v4_flash_0731_cover_square.png']:
    im = Image.open(p).convert('RGB')
    st = ImageStat.Stat(im)
    size_kb = os.path.getsize(p) / 1024
    print(os.path.basename(p), im.size, '%.1f KB' % size_kb,
          'meanRGB=', tuple(round(x, 1) for x in st.mean),
          'stddev=', tuple(round(x, 1) for x in st.stddev))
