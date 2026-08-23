# -*- coding: utf-8 -*-
"""生成对比图：老周定妆4张 2x2 + 第一章10张 5x2 缩略图"""
import os
from PIL import Image, ImageDraw

BASE = r"D:\7tan\7tanAI\镜像同事_小说"
DZ = os.path.join(BASE, "定妆图")
IMG = os.path.join(BASE, "images")

# 1) 老周 4 张 2x2
lz_files = ["character_laozhou_main.png", "character_laozhou_side.png",
            "character_laozhou_face.png", "character_laozhou_full.png"]
thumbs = []
for f in lz_files:
    im = Image.open(os.path.join(DZ, f)).convert("RGB")
    im.thumbnail((480, 480))
    thumbs.append(im)
W, H = 480, 480
canvas = Image.new("RGB", (W * 2 + 30, H * 2 + 30), (30, 30, 30))
draw = ImageDraw.Draw(canvas)
labels = ["main 正面", "side 侧脸基准", "face 特写", "full 全身"]
for i, (im, label) in enumerate(zip(thumbs, labels)):
    x = (i % 2) * (W + 10) + 10
    y = (i // 2) * (H + 10) + 10
    canvas.paste(im, (x, y))
    draw.text((x + 10, y + 10), label, fill=(255, 255, 0))
canvas.save(os.path.join(DZ, "_compare_laozhou.png"))
print("saved _compare_laozhou.png", canvas.size)

# 2) 第一章 10 张 5x2
ch_files = ["ch01_%02d.png" % i for i in range(1, 11)]
thumbs2 = []
for f in ch_files:
    im = Image.open(os.path.join(IMG, f)).convert("RGB")
    im.thumbnail((200, 360))
    thumbs2.append(im)
TW, TH = 200, 360
canvas2 = Image.new("RGB", (TW * 5 + 60, TH * 2 + 50), (30, 30, 30))
draw2 = ImageDraw.Draw(canvas2)
for i, im in enumerate(thumbs2):
    x = (i % 5) * (TW + 10) + 10
    y = (i // 5) * (TH + 10) + 10
    canvas2.paste(im, (x, y))
    draw2.text((x + 5, y + 5), "ch01_%02d" % (i + 1), fill=(255, 255, 0))
canvas2.save(os.path.join(IMG, "_compare_ch01.png"))
print("saved _compare_ch01.png", canvas2.size)
