# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont

base = r'cover_base_v3_3.png'
img = Image.open(base).convert('RGB')
W, H = img.size

def find_font(size):
    for p in [r'C:\Windows\Fonts\msyhbd.ttc', r'C:\Windows\Fonts\msyh.ttc',
              r'C:\Windows\Fonts\simhei.ttf', r'C:\Windows\Fonts\simsun.ttc']:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

line1 = '游资是怎样'
line2 = '炼成的'
RED = (230, 30, 30)
draw = ImageDraw.Draw(img)

# 字号：第一行 5 字铺约 86% 宽度，字够大
target_w = int(W * 0.86)
size = 220
while size > 40:
    f = find_font(size)
    b = draw.textbbox((0, 0), line1, font=f)
    if (b[2] - b[0]) <= target_w:
        break
    size -= 2
font = find_font(size)

b1 = draw.textbbox((0, 0), line1, font=font)
w1 = b1[2] - b1[0]; h1 = b1[3] - b1[1]
b2 = draw.textbbox((0, 0), line2, font=font)
w2 = b2[2] - b2[0]; h2 = b2[3] - b2[1]

gap = int(size * 0.16)
total_h = h1 + gap + h2
bottom_margin = int(H * 0.04)
y_top = H - bottom_margin - total_h
y2_top = y_top + h1 + gap

def draw_center(cx, cy, txt, font):
    bb = draw.textbbox((0, 0), txt, font=font)
    tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    x = cx - tw // 2
    y = cy - th // 2 - bb[1]
    draw.text((x, y), txt, font=font, fill=RED,
              stroke_width=max(2, font.size // 38), stroke_fill=(255, 255, 255))

cx = W // 2
draw_center(cx, y_top + h1 // 2, line1, font)
draw_center(cx, y2_top + h2 // 2, line2, font)

img.save('cover_游资是怎样炼成的.png')
img.save('cover_游资是怎样炼成的.jpg', quality=92)
print('done. size=%d w1=%d w2=%d y_top=%d' % (size, w1, w2, y_top))
