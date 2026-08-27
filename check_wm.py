# -*- coding: utf-8 -*-
"""检查去水印后的视频右下角是否还有残留痕迹"""
from PIL import Image

for n in ['1', '5', '9']:
    im = Image.open(f'downloads/video_test/ch01/check_f{n}.png')
    # 右下角区域: x 680-1080, y 1700-1920
    crop = im.crop((680, 1700, 1080, 1920))
    crop = crop.resize((1200, 660), Image.NEAREST)
    crop.save(f'downloads/video_test/ch01/zoom_f{n}.png')
    print(f'zoom_f{n}.png saved')
print('DONE')
