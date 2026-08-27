# -*- coding: utf-8 -*-
"""《偏差》第五章横版封面 1920x1080：左文右图布局，与竖版同风格（冷蓝悬疑+红色点缀）"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os

BASE = r"D:\7tan\7tanAI\镜像同事_小说\images\第5章\ch05_m09.png"
OUT_PNG = r"D:\7tan\7tanAI\镜像同事_小说\video\偏差_第05章_封面_横版.png"
OUT_JPG = r"D:\7tan\7tanAI\镜像同事_小说\video\偏差_第05章_封面_横版.jpg"

W, H = 1920, 1080
RED = (192, 57, 43)
WHITE = (255, 255, 255)
SOFT = (226, 232, 240)

src = Image.open(BASE).convert("RGB")

# ---------- 1. 背景：竖图 cover 放大裁剪 -> 模糊 -> 压暗 ----------
scale = W / src.width
bh = int(src.height * scale)
bg = src.resize((W, bh), Image.LANCZOS)
top = (bh - H) // 2
bg = bg.crop((0, top, W, top + H)).filter(ImageFilter.GaussianBlur(16)).convert("RGBA")
bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (4, 9, 17, 150)))

# 渐变：左侧压暗放文字 + 底部轻压暗（先画在同一层再合成）
grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(grad)
for x in range(1280):
    a = int(205 * (1 - x / 1280) ** 1.25)
    gd.line([(x, 0), (x, H)], fill=(3, 6, 12, a))
for y in range(900, H):
    t = (y - 900) / (H - 900)
    gd.line([(0, y), (W, y)], fill=(3, 6, 12, int(130 * t ** 1.3)))
bg = Image.alpha_composite(bg, grad)

# ---------- 2. 右侧原图（带阴影+细边框） ----------
ph = 940
pw = int(src.width * ph / src.height)      # 528
fg = src.resize((pw, ph), Image.LANCZOS).convert("RGBA")
fx, fy = W - pw - 72, (H - ph) // 2        # 1320, 70

sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(sh)
sd.rounded_rectangle([fx + 12, fy + 16, fx + pw + 12, fy + ph + 16],
                     radius=16, fill=(0, 0, 0, 170))
sh = sh.filter(ImageFilter.GaussianBlur(20))
bg = Image.alpha_composite(bg, sh)
bg.alpha_composite(fg, (fx, fy))
dd = ImageDraw.Draw(bg)
dd.rounded_rectangle([fx - 3, fy - 3, fx + pw + 3, fy + ph + 3],
                     radius=10, outline=(255, 255, 255, 70), width=3)

# ---------- 3. 文字工具 ----------
def draw_glow_text(base, xy, txt, font, fill, anchor="lm",
                   shadow=(0, 0, 0), blur=10, s_alpha=230):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text(xy, txt, font=font, fill=shadow + (s_alpha,), anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)
    d = ImageDraw.Draw(base)
    d.text(xy, txt, font=font, fill=fill + (255,), anchor=anchor)

F_HEI = r"C:\Windows\Fonts\simhei.ttf"
F_YA = r"C:\Windows\Fonts\msyhbd.ttc"
f_badge_top = ImageFont.truetype(F_YA, 38)
f_brand     = ImageFont.truetype(F_HEI, 172)
f_chap_tag  = ImageFont.truetype(F_YA, 42)
f_title     = ImageFont.truetype(F_HEI, 122)
f_hook      = ImageFont.truetype(F_YA, 45)

LX = 116  # 左边距

# ---------- 4. 左侧文字区 ----------
draw_glow_text(bg, (LX, 128), "职 场 悬 疑 · 连 载 短 篇",
               f_badge_top, (208, 220, 232), blur=6, s_alpha=200)
draw_glow_text(bg, (LX, 300), "偏 差", f_brand, WHITE, blur=14, s_alpha=240)
dd.rounded_rectangle([LX + 4, 424, LX + 268, 434], radius=5, fill=RED + (235,))

# 红色「第五章」徽标
tag_w, tag_h = 190, 62
dd.rounded_rectangle([LX, 512, LX + tag_w, 512 + tag_h], radius=12, fill=RED + (242,))
dd.text((LX + tag_w // 2, 512 + tag_h // 2 - 2), "第 五 章",
        font=f_chap_tag, fill=WHITE + (255,), anchor="mm")

# 章节主标题
draw_glow_text(bg, (LX, 668), "工牌上的脸", f_title, WHITE, blur=13, s_alpha=245)

# 钩子文案两行（关键词暖红点亮）
def draw_hook_line(y, parts):
    x = LX
    for t, is_red in parts:
        col = (238, 106, 92) if is_red else SOFT
        draw_glow_text(bg, (x, y), t, f_hook, col, anchor="lm", blur=6, s_alpha=210)
        x += dd.textlength(t, font=f_hook)

draw_hook_line(806, [("工牌照片里的人，", False), ("老了二十岁", True), ("，", False)])
draw_hook_line(876, [("却穿着他", False), ("今天刚换的衬衫", True), ("。", False)])

# ---------- 5. 输出 ----------
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
final = bg.convert("RGB")
final.save(OUT_PNG)
final.save(OUT_JPG, quality=92)
print("PNG:", OUT_PNG, os.path.getsize(OUT_PNG), "bytes")
print("JPG:", OUT_JPG, os.path.getsize(OUT_JPG), "bytes")
print("SIZE:", final.size)
