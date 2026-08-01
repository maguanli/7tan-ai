# -*- coding: utf-8 -*-
"""验证生成的封面图"""
from PIL import Image
import os

img = Image.open('downloads/covers/ds_v4_flash_0731_cover.png')
print('尺寸:', img.size, '模式:', img.mode)
for name, xy in [('左上',(100,100)), ('中心',(960,540)), ('标题区',(960,420)), ('徽章区',(960,585)), ('右下',(1800,1000))]:
    print(name, img.getpixel(xy))
print('文件大小:', os.path.getsize('downloads/covers/ds_v4_flash_0731_cover.png'), 'bytes')

sq = Image.open('downloads/covers/ds_v4_flash_0731_cover_square.png')
print('方形版:', sq.size, os.path.getsize('downloads/covers/ds_v4_flash_0731_cover_square.png'), 'bytes')
