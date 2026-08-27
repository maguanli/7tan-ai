# -*- coding: utf-8 -*-
"""增强对比度检查delogo区域是否有残留痕迹 + 检查全画面四角"""
from PIL import Image, ImageOps

# 1) 对水印修复区域做直方图均衡化（放大微弱痕迹）
for n in ['1', '5', '9']:
    im = Image.open(f'downloads/video_test/ch01/check_f{n}.png').convert('L')
    # 水印原位置 x=829~1023, y=1820~1881，外扩边距
    crop = im.crop((790, 1790, 1060, 1910))
    eq = ImageOps.autocontrast(crop, cutoff=1)
    eq = eq.resize((1080, 480), Image.NEAREST)
    eq.save(f'downloads/video_test/ch01/eq_f{n}.png')
    print(f'eq_f{n}.png saved')

# 2) 全画面四角拼图（检查是否还有其他角落的水印）
im = Image.open('downloads/video_test/ch01/check_f5.png')
w, h = im.size
corners = {
    'TL': (0, 0, 400, 220),
    'TR': (w-400, 0, w, 220),
    'BL': (0, h-220, 400, h),
}
canvas = Image.new('RGB', (1200, 660))
for i, (name, box) in enumerate(corners.items()):
    c = im.crop(box).resize((400, 220), Image.NEAREST)
    canvas.paste(c, (i*400, 0))
canvas.save('downloads/video_test/ch01/corners_f5.png')
print('corners_f5.png saved')
print('DONE')
