# -*- coding: utf-8 -*-
"""《游资是怎样炼成的》写实封面 v3：干净底图 + 书名排版"""
import os
from PIL import Image, ImageDraw, ImageFont

IMG_SRC = r"D:\7tan\7tanAI\陈小群\cover\cover_base_v3_1.png"
OUT_DIR = r"D:\7tan\7tanAI\陈小群"
OUT_PNG = os.path.join(OUT_DIR, "cover_游资是怎样炼成的.png")
OUT_JPG = os.path.join(OUT_DIR, "cover_游资是怎样炼成的.jpg")

FONT_TITLE = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_SUB = r"C:\Windows\Fonts\msyh.ttc"

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def main():
    im = Image.open(IMG_SRC).convert("RGB")
    W, H = im.size
    print("底图尺寸:", W, H)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    top = int(H * 0.60)
    for y in range(top, H):
        t = (y - top) / max(1, H - top)
        alpha = int(30 + 175 * (t ** 1.3))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(im)

    title = "游资是怎样炼成的"
    f_title = load_font(FONT_TITLE, 68)
    tb = draw.textbbox((0, 0), title, font=f_title)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    ty = int(H * 0.72)
    tx = (W - tw) // 2
    sw = 4
    draw.text((tx, ty), title, font=f_title, fill=(0, 0, 0, 255),
              stroke_width=sw, stroke_fill=(0, 0, 0, 255))
    draw.text((tx, ty), title, font=f_title, fill=(255, 255, 255, 255))

    sub = "从8万到15亿 · 一个草根的炼成"
    f_sub = load_font(FONT_SUB, 30)
    sb = draw.textbbox((0, 0), sub, font=f_sub)
    sw2, sh2 = sb[2] - sb[0], sb[3] - sb[1]
    sy = ty + th + int(H * 0.03)
    sx = (W - sw2) // 2
    draw.text((sx, sy), sub, font=f_sub, fill=(255, 214, 110, 255),
              stroke_width=2, stroke_fill=(0, 0, 0, 255))

    im.save(OUT_PNG)
    im.save(OUT_JPG, quality=93)
    print("已保存:")
    print("  ", OUT_PNG, os.path.getsize(OUT_PNG), "bytes")
    print("  ", OUT_JPG, os.path.getsize(OUT_JPG), "bytes")

if __name__ == "__main__":
    main()
