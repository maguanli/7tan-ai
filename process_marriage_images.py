# -*- coding: utf-8 -*-
"""处理婚姻案文章图片：封面裁剪900x383 + 正文图压缩1080px"""
from PIL import Image
import os

SRC = 'downloads/marriage_article'
OUT = 'downloads/marriage_article/final'
os.makedirs(OUT, exist_ok=True)

# 1. 封面裁剪为 900x383 (2.35:1)
cover_src = os.path.join(SRC, 'cover_candidate_man_crying.jpg')
cover = Image.open(cover_src)
w, h = cover.size
target_ratio = 900 / 383  # ≈2.349
# 中心裁剪到目标比例
new_h = int(w / target_ratio)
if new_h > h:
    new_w = int(h * target_ratio)
    left = (w - new_w) // 2
    cover_crop = cover.crop((left, 0, left + new_w, h))
else:
    top = (h - new_h) // 2
    cover_crop = cover.crop((0, top, w, top + new_h))
cover_resized = cover_crop.resize((900, 383), Image.LANCZOS)
cover_out = os.path.join(OUT, 'cover_marriage_900x383.jpg')
cover_resized.save(cover_out, 'JPEG', quality=90)
print(f'封面: {cover_out} {cover_resized.size[0]}x{cover_resized.size[1]}')

# 2. 正文插图压缩到 1080px 宽
img_map = {
    'img1_father_daughter_sunset.jpg': 'img1_father_daughter.jpg',
    'img2_lady_justice.jpg': 'img2_lady_justice.jpg',
    'img3_lonely_man_sunset.jpg': 'img3_lonely_man_sunset.jpg',
}
for src_name, out_name in img_map.items():
    src_path = os.path.join(SRC, src_name)
    im = Image.open(src_path)
    w, h = im.size
    if w > 1080:
        new_h = int(h * 1080 / w)
        im = im.resize((1080, new_h), Image.LANCZOS)
    out_path = os.path.join(OUT, out_name)
    im.save(out_path, 'JPEG', quality=88)
    print(f'正文图: {out_path} {im.size[0]}x{im.size[1]}')
