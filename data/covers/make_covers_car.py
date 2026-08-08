# -*- coding: utf-8 -*-
"""生成《40岁被裁那天，我在车里抽完半包烟》封面/金句卡/正文配图"""
import os, math
from PIL import Image, ImageDraw, ImageFont

OUT = r"D:\7tan\7tanAI\data\covers"
os.makedirs(OUT, exist_ok=True)

FONTS = {
    "yahei": r"C:\Windows\Fonts\msyh.ttc",
    "yahei_bd": r"C:\Windows\Fonts\msyhbd.ttc",
    "hei": r"C:\Windows\Fonts\simhei.ttf",
    "song": r"C:\Windows\Fonts\simsun.ttc",
    "kai": r"C:\Windows\Fonts\simkai.ttf",
}

def font(kind, size):
    return ImageFont.truetype(FONTS[kind], size)

def vgrad(w, h, c1, c2):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img

def stamp(d, xy, text, size=30, color=(200, 40, 40)):
    f = font("kai", size)
    w = f.size * len(text) + 22
    h = f.size + 22
    x, y = xy
    d.rounded_rectangle([x, y, x + w, y + h], radius=6, outline=color, width=3)
    tw = d.textlength(text, font=f)
    d.text((x + (w - tw) / 2, y + 10), text, font=f, fill=color)

def smoke(d, x, y, color=(190, 190, 190)):
    """画一缕烟：从(x,y)向上飘的波浪线"""
    pts = []
    for i in range(24):
        xx = x + math.sin(i * 0.5) * (6 + i * 0.5)
        yy = y - i * 7
        pts.append((xx, yy))
    d.line(pts, fill=color, width=3)

def car(d, x, y, w=260, body=(70, 74, 82), glow=True):
    """画一辆车剪影, 左上角(x,y), 宽w"""
    h = int(w * 0.38)
    roof_h = int(h * 0.55)
    # 车身
    d.rounded_rectangle([x, y + roof_h, x + w, y + h], radius=12, fill=body, outline=(140, 145, 155), width=3)
    # 车顶
    d.rounded_rectangle([x + int(w*0.18), y, x + int(w*0.72), y + roof_h + 8], radius=14, fill=body, outline=(140, 145, 155), width=3)
    # 车窗
    d.rounded_rectangle([x + int(w*0.24), y + 10, x + int(w*0.42), y + roof_h - 4], radius=6, fill=(30, 34, 44), outline=(120, 126, 136), width=2)
    d.rounded_rectangle([x + int(w*0.50), y + 10, x + int(w*0.66), y + roof_h - 4], radius=6, fill=(30, 34, 44), outline=(120, 126, 136), width=2)
    # 轮子
    r = int(h * 0.22)
    for cx in (x + int(w*0.22), x + int(w*0.78)):
        d.ellipse([cx - r, y + h - r - 4, cx + r, y + h + r - 4], fill=(12, 12, 14), outline=(100, 100, 105), width=2)
    # 车灯
    if glow:
        d.ellipse([x + w - 6, y + int(h*0.55), x + w + 10, y + int(h*0.70)], fill=(255, 226, 140))
        d.line([(x + w, y + int(h*0.58)), (x + w + 70, y + int(h*0.52))], fill=(255, 226, 140), width=3)
        d.line([(x + w, y + int(h*0.62)), (x + w + 60, y + int(h*0.60))], fill=(255, 226, 140), width=2)

# ---------- 1. 主封面 900x383：深夜停车场·车里抽烟 ----------
W, H = 900, 383
img = vgrad(W, H, (24, 26, 32), (8, 8, 10))
d = ImageDraw.Draw(img)
# 地面
d.rectangle([0, 300, W, H], fill=(16, 16, 20))
d.line([(0, 300), (W, 300)], fill=(90, 94, 100), width=2)
# 远处水泥柱
for i, cx in enumerate([80, 260, 620, 800]):
    d.rectangle([cx, 190, cx + 46, 300], fill=(36, 40, 48), outline=(70, 74, 82), width=2)
# 车（右侧）
car(d, 520, 190, w=300)
# 烟（从车窗飘出）
smoke(d, 610, 190, (200, 200, 200))
# 标题
d.text((36, 34), "大起大落的一生 · 老马", font=font("kai", 26), fill=(190, 190, 190))
d.text((36, 100), "40岁被裁那天", font=font("yahei_bd", 64), fill=(245, 245, 245))
d.text((36, 180), "我在车里抽完半包烟", font=font("yahei_bd", 52), fill=(214, 92, 60))
d.line([(36, 258), (460, 258)], fill=(120, 120, 120), width=2)
d.text((36, 272), "—— 写给所有在硬撑的中年人", font=font("song", 24), fill=(150, 150, 150))
img.save(os.path.join(OUT, "cover_car.png"), "JPEG", quality=92)
print("saved cover_car.png", img.size)

# ---------- 2. 备用封面 900x383：深蓝极简 ----------
img = vgrad(W, H, (26, 38, 56), (10, 16, 26))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, 8], fill=(214, 92, 60))
d.text((40, 48), "大起大落的一生", font=font("kai", 30), fill=(160, 180, 205))
d.text((40, 118), "40岁被裁那天", font=font("yahei_bd", 66), fill=(255, 255, 255))
d.text((40, 202), "我在车里抽完半包烟", font=font("yahei_bd", 56), fill=(214, 92, 60))
d.text((40, 320), "作者：老马 ｜ 公众号：大起大落的一生", font=font("kai", 26), fill=(150, 170, 195))
img.save(os.path.join(OUT, "cover_car_blue.png"), "JPEG", quality=92)
print("saved cover_car_blue.png", img.size)

# ---------- 3. 金句卡1 1080x608 ----------
W2, H2 = 1080, 608
img = vgrad(W2, H2, (16, 16, 18), (8, 8, 10))
d = ImageDraw.Draw(img)
d.text((70, 40), "\u201c", font=font("song", 150), fill=(80, 80, 85))
d.text((70, 240), "成年人不是不怕，", font=font("kai", 56), fill=(240, 240, 240))
d.text((70, 320), "是怕完还得站起来。", font=font("kai", 56), fill=(240, 240, 240))
d.line([(80, 440), (1000, 440)], fill=(120, 120, 120), width=2)
d.text((80, 460), "—— 老马 · 大起大落的一生", font=font("kai", 34), fill=(170, 170, 170))
stamp(d, (880, 460), "老马", 32)
img.save(os.path.join(OUT, "quote_car1.png"), "JPEG", quality=92)
print("saved quote_car1.png", img.size)

# ---------- 4. 金句卡2 1080x608 ----------
img = vgrad(W2, H2, (22, 20, 16), (10, 9, 7))
d = ImageDraw.Draw(img)
d.text((70, 40), "\u201c", font=font("song", 150), fill=(90, 80, 60))
d.text((70, 230), "中年人的体面，", font=font("kai", 56), fill=(240, 238, 230))
d.text((70, 310), "是明明天塌了，", font=font("kai", 56), fill=(240, 238, 230))
d.text((70, 390), "还要假装只是下班晚了。", font=font("kai", 56), fill=(214, 92, 60))
d.line([(80, 480), (1000, 480)], fill=(120, 110, 90), width=2)
d.text((80, 500), "—— 老马 · 大起大落的一生", font=font("kai", 34), fill=(170, 160, 140))
stamp(d, (880, 500), "老马", 32)
img.save(os.path.join(OUT, "quote_car2.png"), "JPEG", quality=92)
print("saved quote_car2.png", img.size)

# ---------- 5. 正文插图1 750x422：地下车库 ----------
W3, H3 = 750, 422
img = vgrad(W3, H3, (30, 32, 38), (10, 10, 12))
d = ImageDraw.Draw(img)
d.rectangle([0, 330, W3, H3], fill=(18, 18, 22))
d.line([(0, 330), (W3, 330)], fill=(90, 94, 100), width=2)
for i, cx in enumerate([60, 250, 480, 660]):
    d.rectangle([cx, 220, cx + 40, 330], fill=(38, 42, 50), outline=(70, 74, 82), width=2)
car(d, 430, 220, w=250)
smoke(d, 510, 222, (200, 200, 200))
d.text((30, 40), "地下车库 · 下午三点", font=font("kai", 30), fill=(210, 210, 210))
d.text((30, 100), "手机亮了三次，是老婆的未接来电。", font=font("kai", 26), fill=(150, 150, 155))
d.text((30, 140), "我盯着那串学费数字，没有接。", font=font("kai", 26), fill=(150, 150, 155))
img.save(os.path.join(OUT, "article_car1.png"), "JPEG", quality=92)
print("saved article_car1.png", img.size)

# ---------- 6. 正文插图2 750x422：校门口接孩子 ----------
img = vgrad(W3, H3, (40, 44, 30), (14, 16, 10))
d = ImageDraw.Draw(img)
# 路灯
d.rectangle([560, 60, 572, 300], fill=(70, 74, 66))
d.ellipse([536, 30, 596, 90], fill=(255, 230, 150))
# 光晕
for r, a in [(70, 70), (110, 45), (150, 25)]:
    d.ellipse([536 - r, 60 - r, 596 + r, 90 + r], outline=(255, 230, 150, a))
# 大人+小孩剪影
def person(d, cx, top, h, color=(20, 22, 18)):
    r = int(h * 0.12)
    d.ellipse([cx - r, top, cx + r, top + r * 2], fill=color)
    d.rounded_rectangle([cx - int(h*0.16), top + r * 2, cx + int(h*0.16), top + int(h*0.62)], radius=8, fill=color)
    d.rounded_rectangle([cx - int(h*0.30), top + int(h*0.55), cx + int(h*0.30), top + h], radius=10, fill=color)
person(d, 340, 130, 170)
person(d, 420, 220, 100)
d.text((30, 40), "晚上六点 · 学校门口", font=font("kai", 30), fill=(230, 225, 210))
d.text((30, 110), "\u201c爸，你今天要是累了，", font=font("kai", 28), fill=(200, 195, 180))
d.text((30, 150), "我可以自己走回家。\u201d", font=font("kai", 28), fill=(200, 195, 180))
img.save(os.path.join(OUT, "article_car2.png"), "JPEG", quality=92)
print("saved article_car2.png", img.size)

# 拼一张预览图
imgs = [Image.open(os.path.join(OUT, n)) for n in
        ["cover_car.png", "cover_car_blue.png", "quote_car1.png", "quote_car2.png", "article_car1.png", "article_car2.png"]]
pw, ph = 480, 240
canvas = Image.new("RGB", (pw * 3, ph * 2), (30, 30, 30))
for i, im in enumerate(imgs):
    im2 = im.resize((pw, ph))
    canvas.paste(im2, ((i % 3) * pw, (i // 3) * ph))
canvas.save(os.path.join(OUT, "preview_car.png"), "JPEG", quality=90)
print("saved preview_car.png")
print("ALL DONE")
