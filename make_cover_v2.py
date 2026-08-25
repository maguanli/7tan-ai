# -*- coding: utf-8 -*-
"""重新生成 ch03_08 封面：偏差(红)与身在局外著(白)拉开间距"""
from PIL import Image, ImageDraw, ImageFont
import os

SRC = r"D:\用户目录\下载\新建文件夹 123\ch03_08.png"
OUT = r"D:\用户目录\下载\新建文件夹 123\ch03_08_封面.png"

im = Image.open(SRC).convert("RGB")
W, H = im.size
print("原图尺寸:", W, H)

draw = ImageDraw.Draw(im)

# 1. 底部渐变压暗遮罩（从 55% 高度开始渐变到全黑边缘）
alpha = Image.new("L", (1, H), 0)
for y in range(H):
    t = y / H
    if t > 0.52:
        alpha.putpixel((0, y), int(180 * (t - 0.52) / 0.48))
    else:
        alpha.putpixel((0, y), 0)
black = Image.new("RGB", (W, H), (0, 0, 0))
im.paste(black, (0, 0), alpha.resize((W, H)))

# 2. 找可用中文字体
font_paths = [
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑 Bold
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]
font_path = None
for fp in font_paths:
    if os.path.exists(fp):
        font_path = fp
        break
if not font_path:
    raise FileNotFoundError("无中文字体")
print("字体:", font_path)

# 3. 文字参数：主标题 100px 红色，副标题 50px 白色，间距拉大
title_font = ImageFont.truetype(font_path, 100)
sub_font = ImageFont.truetype(font_path, 50)

def draw_text_center(draw, text, font, y_center, fill, stroke_fill=(0, 0, 0), stroke_w=4):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (W - tw) // 2 - bbox[0]
    y = y_center - th // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)

# 主标题「偏 差」在 68% 高度（红色大字）
title_y = int(H * 0.68)
draw_text_center(draw, "偏 差", title_font, title_y, (220, 30, 30), stroke_fill=(0, 0, 0), stroke_w=6)

# 副标题「身在局外著」在 90% 高度（白色，间距拉大）
sub_y = int(H * 0.90)
draw_text_center(draw, "身在局外著", sub_font, sub_y, (255, 255, 255), stroke_fill=(0, 0, 0), stroke_w=4)

im.save(OUT, "PNG")
print("已保存:", OUT)
print("文件大小:", os.path.getsize(OUT), "bytes")
