# -*- coding: utf-8 -*-
"""DeepSeek-V4-Flash-0731 正式版上线 封面图生成器"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

W, H = 1920, 1080
OUT = "downloads/covers/deepseek_v4_flash_0731_cover.png"
OUT_SQ = "downloads/covers/deepseek_v4_flash_0731_cover_square.png"
random.seed(7)

def load(path, size):
    return ImageFont.truetype(path, size)

F_BRAND = load(r"C:\Windows\Fonts\Dengb.ttf", 30)
F_TITLE = load(r"C:\Windows\Fonts\msyhbd.ttc", 84)
F_BADGE = load(r"C:\Windows\Fonts\msyhbd.ttc", 48)
F_SUB   = load(r"C:\Windows\Fonts\msyh.ttc", 36)
F_SMALL = load(r"C:\Windows\Fonts\msyh.ttc", 26)

# ---------- 1. 垂直渐变背景 ----------
def vertical_gradient(w, h, stops):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        if t < 0.5:
            tt, c1, c2 = t * 2, stops[0], stops[1]
        else:
            tt, c1, c2 = (t - 0.5) * 2, stops[1], stops[2]
        r = int(c1[0] + (c2[0] - c1[0]) * tt)
        g = int(c1[1] + (c2[1] - c1[1]) * tt)
        b = int(c1[2] + (c2[2] - c1[2]) * tt)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    return img

img = vertical_gradient(W, H, [(7, 10, 34), (18, 30, 84), (5, 8, 28)]).convert("RGBA")

# ---------- 2. 中心光晕 ----------
glow = Image.new("RGB", (W, H), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([W*0.5-520, H*0.5-420, W*0.5+520, H*0.5+420], fill=(40, 80, 200))
glow = glow.filter(ImageFilter.GaussianBlur(220))
img = Image.blend(img, glow.convert("RGBA"), 0.45)

def orb(img, cx, cy, rad, color, alpha, blur=150):
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.paste(Image.blend(img.convert("RGB"), layer, alpha))

orb(img, 250, 230, 260, (0, 140, 255), 0.35)
orb(img, 1720, 880, 300, (60, 90, 220), 0.30)
orb(img, 1650, 200, 180, (0, 200, 220), 0.28)
orb(img, 320, 900, 200, (30, 60, 180), 0.30)

# ---------- 3. 科技网格 ----------
grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(grid)
for x in range(0, W, 90):
    gd.line([(x, 0), (x, H)], fill=(120, 160, 255, 22), width=1)
for y in range(0, H, 90):
    gd.line([(0, y), (W, y)], fill=(120, 160, 255, 22), width=1)
img = Image.alpha_composite(img, grid)

# ---------- 4. 粒子 ----------
part = Image.new("RGBA", (W, H), (0, 0, 0, 0))
pd = ImageDraw.Draw(part)
for _ in range(170):
    x, y = random.randint(0, W), random.randint(0, H)
    r = random.choice([1, 1, 1, 2, 2, 3])
    a = random.randint(50, 190)
    c = random.choice([(150, 220, 255), (255, 255, 255), (110, 200, 255), (200, 230, 255)])
    pd.ellipse([x-r, y-r, x+r, y+r], fill=c + (a,))
img = Image.alpha_composite(img, part)

# ---------- 5. 中心光束 ----------
beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(beam)
bd.rectangle([W//2-230, 180, W//2+230, 920], fill=(90, 140, 255, 55))
beam = beam.filter(ImageFilter.GaussianBlur(130))
img = Image.alpha_composite(img, beam)

# ---------- 6. 装饰光环 ----------
ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rd = ImageDraw.Draw(ring)
rd.ellipse([960-360, 470-360, 960+360, 470+360], outline=(110, 170, 255, 65), width=2)
rd.ellipse([960-420, 410-420, 960+420, 410+420], outline=(110, 170, 255, 35), width=1)
img = Image.alpha_composite(img, ring)

# ---------- 7. 四角装饰线 ----------
accent = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ad = ImageDraw.Draw(accent)
L = 95
for (cx, cy, sx, sy) in [(60, 60, 1, 1), (W-60, 60, -1, 1), (60, H-60, 1, -1), (W-60, H-60, -1, -1)]:
    ad.line([(cx, cy), (cx + sx*L, cy)], fill=(130, 190, 255, 190), width=3)
    ad.line([(cx, cy), (cx, cy + sy*L)], fill=(130, 190, 255, 190), width=3)
img = Image.alpha_composite(img, accent)

# ---------- 8. 工具函数：文字 ----------
def draw_tracked(draw, cx, cy, text, font, fill, tracking):
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, cy), ch, font=font, fill=fill, anchor="lm")
        x += w + tracking

def gradient_text(img, text, font, cx, cy, colors, glow_color, glow_alpha=130, blur=26):
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.text((cx, cy), text, font=font, fill=255, anchor="mm")
    grad = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for x in range(W):
        t = x / (W - 1)
        if t < 0.5:
            tt, c1, c2 = t * 2, colors[0], colors[1]
        else:
            tt, c1, c2 = (t - 0.5) * 2, colors[1], colors[2]
        gd.line([(x, 0), (x, H)], fill=(int(c1[0]+(c2[0]-c1[0])*tt),
                                        int(c1[1]+(c2[1]-c1[1])*tt),
                                        int(c1[2]+(c2[2]-c1[2])*tt)))
    gm = mask.filter(ImageFilter.GaussianBlur(blur))
    gl = Image.new("RGBA", (W, H), glow_color + (0,))
    gl.putalpha(gm.point(lambda p: min(255, int(p * glow_alpha / 255))))
    img = Image.alpha_composite(img, gl)
    tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tl.paste(grad.convert("RGBA"), (0, 0), mask)
    img = Image.alpha_composite(img, tl)
    return img

def rounded_badge(img, text, font, cx, cy, pad_x, pad_y, c1, c2, glow=True):
    bbox = font.getbbox(text)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    w, h = tw + pad_x*2, th + pad_y*2
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([cx-w//2, cy-h//2, cx+w//2, cy+h//2], radius=h//2, fill=255)
    grad = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for x in range(int(cx-w//2), int(cx+w//2)):
        t = (x - (cx-w//2)) / w
        gd.line([(x, 0), (x, H)], fill=(int(c1[0]+(c2[0]-c1[0])*t),
                                        int(c1[1]+(c2[1]-c1[1])*t),
                                        int(c1[2]+(c2[2]-c1[2])*t)))
    if glow:
        gm = mask.filter(ImageFilter.GaussianBlur(18))
        gl = Image.new("RGBA", (W, H), c2 + (0,))
        gl.putalpha(gm.point(lambda p: int(p * 0.55)))
        img = Image.alpha_composite(img, gl)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(grad.convert("RGBA"), (0, 0), mask)
    bd = ImageDraw.Draw(layer)
    bd.rounded_rectangle([cx-w//2, cy-h//2, cx+w//2, cy+h//2],
                         radius=h//2, outline=(255, 255, 255, 130), width=2)
    img = Image.alpha_composite(img, layer)
    tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tl)
    td.text((cx, cy+2), text, font=font, fill=(255, 255, 255), anchor="mm")
    img = Image.alpha_composite(img, tl)
    return img

# ---------- 9. 顶部品牌 ----------
brand = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(brand)
draw_tracked(bd, 960, 168, "D E E P S E E K", F_BRAND, (140, 205, 255, 235), 14)
bd.text((960, 215), "深 度 求 索", font=load(r"C:\Windows\Fonts\msyh.ttc", 24),
        fill=(150, 180, 240, 200), anchor="mm")
img = Image.alpha_composite(img, brand)

# ---------- 10. 主标题 ----------
img = gradient_text(img, "DeepSeek-V4-Flash-0731", F_TITLE, 960, 415,
                    [(255, 255, 255), (130, 205, 255), (100, 150, 255)],
                    (60, 140, 255), glow_alpha=140, blur=30)

# ---------- 11. 正式版徽章 ----------
img = rounded_badge(img, "正式版上线", F_BADGE, 960, 565, 40, 16,
                    (0, 110, 255), (0, 200, 230), glow=True)

# ---------- 12. 副标题 ----------
sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(sub)
sd.text((960, 690), "更快 · 更稳 · 更智能 —— 新一代 Flash 推理引擎", font=F_SUB,
        fill=(205, 220, 255, 230), anchor="mm")
img = Image.alpha_composite(img, sub)

# ---------- 13. 底部信息 ----------
foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
fd = ImageDraw.Draw(foot)
draw_tracked(fd, 960, 810, "O F F I C I A L   R E L E A S E", F_SMALL, (150, 175, 230, 210), 6)
fd.text((960, 880), "2025.07.31  ·  全平台开放下载", font=F_SMALL,
        fill=(130, 155, 215, 190), anchor="mm")
img = Image.alpha_composite(img, foot)

# ---------- 14. 星芒点缀 ----------
spark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
spd = ImageDraw.Draw(spark)
def sparkle(d, x, y, r, color):
    d.line([(x-r, y), (x+r, y)], fill=color, width=2)
    d.line([(x, y-r), (x, y+r)], fill=color, width=2)
for (x, y, r) in [(755, 330, 12), (1185, 300, 8), (700, 640, 9), (1245, 520, 13), (760, 500, 6)]:
    sparkle(spd, x, y, r, (200, 235, 255, 220))
spark = spark.filter(ImageFilter.GaussianBlur(0.6))
img = Image.alpha_composite(img, spark)

# ---------- 15. 输出 ----------
import os
os.makedirs("downloads/covers", exist_ok=True)
final = img.convert("RGB")
final.save(OUT, quality=95)
# 方形版本
sq = final.crop(((W-H)//2, 0, (W-H)//2 + H, H))
sq.save(OUT_SQ, quality=95)
print("OK:", OUT, final.size)
print("OK:", OUT_SQ, sq.size)
