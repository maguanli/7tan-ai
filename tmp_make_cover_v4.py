# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import os

SRC = r"D:\用户目录\下载\新建文件夹 123\ch03_08.png"
DST = r"D:\用户目录\下载\新建文件夹 123\ch03_08_封面.png"

img = Image.open(SRC).convert("RGB")
W, H = img.size

overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(overlay)
for y in range(int(H * 0.58), H):
    t = (y - H * 0.58) / (H * 0.42)
    alpha = int(140 * t)
    od.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
draw = ImageDraw.Draw(img)

def load_font(size):
    for p in [r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\msyh.ttc",
              r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def draw_center(draw, y_top, text, f, fill, stroke_w):
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2 - bbox[0]
    draw.text((x, y_top - bbox[1]), text, font=f, fill=fill,
              stroke_width=stroke_w, stroke_fill=(0, 0, 0, 255))

f_title = load_font(140)
f_sub = load_font(66)

title_y = int(H * 0.70)
sub_y = int(H * 0.855)

draw_center(draw, title_y, "偏 差", f_title, (235, 35, 35, 255), 8)
draw_center(draw, sub_y, "身在局外著", f_sub, (255, 255, 255, 255), 5)

img.save(DST, quality=95)
print("OK", W, H, os.path.getsize(DST))
