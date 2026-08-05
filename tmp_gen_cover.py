# -*- coding: utf-8 -*-
"""生成公众号文章封面图（横图 900x383，公众号推荐比例 2.35:1）"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import random

OUT = os.path.join(os.path.expanduser("~"), "下载", "新建文件夹 123", "11", "公众号封面_免费玩到爽.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
W, H = 900, 383

def load_font(size):
    for path in [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
                 r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

f_title = load_font(64)
f_sub   = load_font(28)
f_small = load_font(20)

# RGBA 全程
img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
px = img.load()
top = (10, 12, 38)
bot = (34, 8, 56)
for y in range(H):
    t = y / H
    r = int(top[0] + (bot[0]-top[0])*t)
    g = int(top[1] + (bot[1]-top[1])*t)
    b = int(top[2] + (bot[2]-top[2])*t)
    for x in range(W):
        px[x, y] = (r, g, b, 255)

glow = Image.new("RGBA", (W, H), (0,0,0,0))
gd = ImageDraw.Draw(glow)
def radial(cx, cy, rad, color):
    for i in range(rad, 0, -1):
        a = int(255 * (1 - i/rad) * 0.55)
        gd.ellipse([cx-i, cy-i, cx+i, cy+i], fill=(color[0], color[1], color[2], a))
radial(160, 100, 260, (40, 90, 220))
radial(760, 300, 240, (150, 40, 200))
radial(700, 80, 180, (0, 180, 200))
glow = glow.filter(ImageFilter.GaussianBlur(60))
img = Image.alpha_composite(img, glow)

grid = Image.new("RGBA", (W, H), (0,0,0,0))
gd = ImageDraw.Draw(grid)
step = 45
for x in range(0, W, step):
    gd.line([(x,0),(x,H)], fill=(120,160,255,26), width=1)
for y in range(0, H, step):
    gd.line([(0,y),(W,y)], fill=(120,160,255,26), width=1)
img = Image.alpha_composite(img, grid)

random.seed(42)
img2 = Image.new("RGBA", (W, H), (0,0,0,0))
gd = ImageDraw.Draw(img2)
for _ in range(140):
    x, y = random.randint(0,W), random.randint(0,H)
    r = random.randint(1,3)
    a = random.randint(60, 200)
    gd.ellipse([x-r, y-r, x+r, y+r], fill=(200,220,255,a))
img = Image.alpha_composite(img, img2)

d = ImageDraw.Draw(img)
card_colors = [(0,140,220), (220,60,120), (0,190,140), (240,160,30)]
for i, c in enumerate(card_colors):
    x0 = 36 + i*56
    y0 = 52 + (i%2)*26
    x1, y1 = x0+44, y0+44
    d.rounded_rectangle([x0,y0,x1,y1], radius=8, outline=c, width=3)
    d.line([(x0+10,y0+22),(x1-10,y0+22)], fill=c, width=3)
    d.ellipse([x0+18,y0+28,x0+26,y0+36], fill=c)

def draw_glow_text(x, y, text, font, fill, glow_color, radius=4):
    global img
    tmp = Image.new("RGBA", (W, H), (0,0,0,0))
    td = ImageDraw.Draw(tmp)
    td.text((x, y), text, font=font, fill=glow_color+(200,))
    tmp = tmp.filter(ImageFilter.GaussianBlur(radius))
    img_tmp = img.copy()
    img_tmp.alpha_composite(tmp)
    img = img_tmp
    d = ImageDraw.Draw(img)
    d.text((x, y), text, font=font, fill=fill)

draw_glow_text(300, 52, "免费玩到爽！", f_title, (255,255,255), (80,200,255), 6)
draw_glow_text(300, 140, "2026年这5款新游良心到爆", f_sub, (150,230,255), (60,120,255), 3)
draw_glow_text(300, 190, "最后一款我通宵了3晚", f_sub, (255,210,90), (255,140,40), 3)

d = ImageDraw.Draw(img)
d.rounded_rectangle([300, 258, 560, 300], radius=21, fill=(36,36,60,180), outline=(120,200,255,120), width=2)
d.text((326, 268), "全部免费下载 · 不氪金", font=f_small, fill=(255,255,255))

d.rounded_rectangle([790, 24, 876, 66], radius=18, fill=(255,80,80,200))
d.text((806, 34), "良心推荐", font=f_small, fill=(255,255,255))

img.convert("RGB").save(OUT, quality=92)
print("COVER_OK", OUT)
