# -*- coding: utf-8 -*-
"""偏差 第七章 视频封面制作"""
from PIL import Image, ImageDraw, ImageFont
import os

SRC = r"D:\用户目录\下载\新建文件夹 123\ch07_m03.png"
OUT_DIR = r"D:\7tan\7tanAI\镜像同事_小说\video"
OUT = os.path.join(OUT_DIR, "偏差_第07章_另一个我_封面.png")

TARGET_W, TARGET_H = 1080, 1920

im = Image.open(SRC).convert("RGB")
print("原始尺寸:", im.size)

sw, sh = im.size
scale = max(TARGET_W / sw, TARGET_H / sh)
nw, nh = int(sw * scale), int(sh * scale)
im = im.resize((nw, nh), Image.LANCZOS)
left = (nw - TARGET_W) // 2
top = (nh - TARGET_H) // 2
im = im.crop((left, top, left + TARGET_W, top + TARGET_H))
print("裁剪后:", im.size)

draw = ImageDraw.Draw(im)

font_candidates = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]

def get_font(size):
    for f in font_candidates:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()

title_main = "偏差"
title_sub = "第七章 · 另一个我"

overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
odraw = ImageDraw.Draw(overlay)
for y in range(500):
    alpha = int(180 * (1 - y / 500))
    odraw.line([(0, y), (TARGET_W, y)], fill=(0, 0, 0, alpha))
im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
draw = ImageDraw.Draw(im)

font_main = get_font(150)
bbox = draw.textbbox((0, 0), title_main, font=font_main)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
tx = (TARGET_W - tw) // 2
ty = 180
draw.text((tx, ty), title_main, font=font_main, fill=(0, 0, 0),
          stroke_width=8, stroke_fill=(0, 0, 0))
draw.text((tx, ty), title_main, font=font_main, fill=(255, 255, 255))

font_sub = get_font(70)
bbox2 = draw.textbbox((0, 0), title_sub, font=font_sub)
tw2 = bbox2[2] - bbox2[0]
tx2 = (TARGET_W - tw2) // 2
ty2 = ty + th + 50
draw.text((tx2, ty2), title_sub, font=font_sub, fill=(255, 255, 255),
          stroke_width=5, stroke_fill=(0, 0, 0))
draw.text((tx2, ty2), title_sub, font=font_sub, fill=(255, 255, 255))

im.save(OUT, quality=95)
print("已保存:", OUT)
print("输出尺寸:", im.size)
