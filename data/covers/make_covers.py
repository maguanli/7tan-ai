# -*- coding: utf-8 -*-
"""生成 7Tan 公众号鲁迅风格封面图/配图"""
import os, random
from PIL import Image, ImageDraw, ImageFont

OUT = r"D:\7tan\7tanAI\data\covers"
os.makedirs(OUT, exist_ok=True)

FONTS = {
    "yahei": r"C:\Windows\Fonts\msyh.ttc",
    "yahei_bd": r"C:\Windows\Fonts\msyhbd.ttc",
    "hei": r"C:\Windows\Fonts\simhei.ttf",
    "song": r"C:\Windows\Fonts\simsun.ttc",
    "kai": r"C:\Windows\Fonts\simkai.ttf",
    "fang": r"C:\Windows\Fonts\simfang.ttf",
}

def font(kind, size):
    return ImageFont.truetype(FONTS[kind], size)

def vgrad(w, h, c1, c2):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    return img

def draw_vtext(d, xy, text, fnt, fill, spacing=8):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        y += fnt.size + spacing
    return y

def stamp(d, xy, text, size=34, color=(200, 40, 40)):
    f = font("kai", size)
    w = f.size * len(text) + 24
    h = f.size + 24
    x, y = xy
    d.rounded_rectangle([x, y, x + w, y + h], radius=6, outline=color, width=3)
    tw = d.textlength(text, font=f)
    d.text((x + (w - tw) / 2, y + 10), text, font=f, fill=color)

def save(img, name):
    p = os.path.join(OUT, name)
    img.save(p, "JPEG", quality=90)
    print("saved", p, img.size)

# ---------- 1. 墨夜红字 900x383（主推封面） ----------
W, H = 900, 383
img = vgrad(W, H, (28, 28, 30), (10, 10, 12))
d = ImageDraw.Draw(img)
d.ellipse([720, 48, 792, 120], fill=(232, 213, 163))
d.polygon([(0, 300), (120, 230), (240, 285), (380, 200), (520, 290), (660, 215), (780, 295), (900, 240), (900, 383), (0, 383)], fill=(18, 18, 22))
d.text((40, 42), "大起大落的一生 · 老马", font=font("kai", 26), fill=(200, 200, 200))
d.text((46, 128), "富贵时都是亲戚", font=font("yahei_bd", 62), fill=(245, 245, 245))
d.text((46, 210), "落难时全是看客", font=font("yahei_bd", 62), fill=(201, 63, 60))
d.line([(48, 300), (852, 300)], fill=(120, 120, 120), width=2)
d.text((48, 318), "—— 鲁迅式冷眼看世态 · 篇一", font=font("song", 24), fill=(150, 150, 150))
save(img, "cover_night.png")

# ---------- 2. 宣纸竖排 900x383 ----------
img = Image.new("RGB", (W, H), (245, 236, 215))
d = ImageDraw.Draw(img)
random.seed(7)
for _ in range(3000):
    x, y = random.randint(0, W - 1), random.randint(0, H - 1)
    v = random.randint(0, 40)
    d.point((x, y), fill=(245 - v, 236 - v, 215 - v))
d.text((560, 60), "大起大落的一生", font=font("kai", 30), fill=(90, 80, 60))
draw_vtext(d, (500, 90), "富贵时都是亲戚", font("song", 54), (30, 25, 20), spacing=14)
draw_vtext(d, (330, 90), "落难时全是看客", font("song", 54), (30, 25, 20), spacing=14)
stamp(d, (150, 280), "老马", 40)
d.text((60, 60), "七 坛 · 文", font=font("kai", 26), fill=(120, 100, 70))
d.text((60, 100), "世 态 炎 凉 录", font=font("kai", 30), fill=(90, 70, 50))
save(img, "cover_xuanzhi.png")

# ---------- 3. 金句卡 1080x608 ----------
W2, H2 = 1080, 608
img = vgrad(W2, H2, (16, 16, 18), (8, 8, 10))
d = ImageDraw.Draw(img)
d.text((70, 60), "“", font=font("song", 150), fill=(80, 80, 85))
d.text((70, 250), "万人捧时，你听见的全是回声；", font=font("kai", 54), fill=(235, 235, 235))
d.text((70, 330), "万人散时，你才听见自己的心跳。", font=font("kai", 54), fill=(235, 235, 235))
d.line([(80, 450), (1000, 450)], fill=(120, 120, 120), width=2)
d.text((80, 470), "—— 老马 · 大起大落的一生", font=font("kai", 34), fill=(170, 170, 170))
stamp(d, (880, 470), "老马", 34)
save(img, "cover_quote.png")

# ---------- 4. 极简深蓝 900x383 ----------
img = vgrad(W, H, (24, 40, 55), (10, 18, 28))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, 8], fill=(201, 63, 60))
d.text((40, 52), "大起大落的一生", font=font("kai", 30), fill=(160, 180, 200))
d.text((40, 130), "富贵时都是亲戚", font=font("yahei_bd", 64), fill=(255, 255, 255))
d.text((40, 216), "落难时全是看客", font=font("yahei_bd", 64), fill=(201, 63, 60))
d.text((40, 320), "作者：老马 ｜ 公众号：大起大落的一生", font=font("kai", 26), fill=(150, 170, 190))
save(img, "cover_minimal.png")

# ---------- 5. 正文插图：铁屋子 750x422 ----------
W3, H3 = 750, 422
img = vgrad(W3, H3, (30, 30, 34), (12, 12, 14))
d = ImageDraw.Draw(img)
d.rectangle([240, 150, 510, 330], outline=(150, 150, 150), width=4)
d.line([240, 150, 375, 90, 510, 150], fill=(150, 150, 150), width=4)
d.rectangle([300, 190, 450, 280], outline=(150, 150, 150), width=3)
d.line([375, 190, 375, 280], fill=(150, 150, 150), width=2)
d.line([300, 235, 450, 235], fill=(150, 150, 150), width=2)
d.rectangle([280, 240, 330, 330], outline=(150, 150, 150), width=3)
d.line([500, 190, 560, 240], fill=(180, 180, 180), width=4)
d.line([560, 240, 560, 250], fill=(180, 180, 180), width=4)
d.text((240, 60), "铁屋子", font=font("kai", 34), fill=(210, 210, 210))
d.text((240, 350), "睡在铁屋子里的人，喊不醒。", font=font("kai", 26), fill=(150, 150, 150))
save(img, "article_house.png")

# ---------- 6. 正文插图：看客 750x422 ----------
img = vgrad(W3, H3, (22, 24, 30), (10, 10, 14))
d = ImageDraw.Draw(img)
random.seed(42)
for i in range(28):
    x = 60 + (i % 7) * 95 + random.randint(-15, 15)
    y = 170 + (i // 7) * 70 + random.randint(-12, 12)
    r = random.randint(10, 20)
    d.ellipse([x - r, y - r, x + r, y + r], outline=(160, 160, 170), width=3)
cx, cy = 375, 220
d.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], outline=(201, 63, 60), width=4)
d.text((60, 60), "看客", font=font("kai", 34), fill=(210, 210, 210))
d.text((60, 350), "他们围了一圈，等看结局。", font=font("kai", 26), fill=(150, 150, 150))
save(img, "article_watcher.png")

print("ALL DONE")
