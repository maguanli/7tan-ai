# -*- coding: utf-8 -*-
"""《偏差》第五章视频封面制作：ch05_m09 为底图
布局：顶部《偏差》品牌区 + 底部章节标题/钩子文案区，冷蓝悬疑风"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os

BASE = r"D:\7tan\7tanAI\镜像同事_小说\images\第5章\ch05_m09.png"
OUT_PNG = r"D:\7tan\7tanAI\镜像同事_小说\video\偏差_第05章_封面_竖版.png"
OUT_JPG = r"D:\7tan\7tanAI\镜像同事_小说\video\偏差_第05章_封面_竖版.jpg"

W, H = 1080, 1920
RED = (192, 57, 43)
WHITE = (255, 255, 255)
SOFT = (226, 232, 240)

im = Image.open(BASE).convert("RGB")
if im.size != (W, H):
    im = im.resize((W, H), Image.LANCZOS)
im = im.convert("RGBA")

# ---------- 1. 渐变遮罩（顶部压暗放书名 / 底部压暗放标题） ----------
grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(grad)
for y in range(480):                       # 顶部渐变
    a = int(170 * (1 - y / 480) ** 1.5)
    gd.line([(0, y), (W, y)], fill=(4, 9, 17, a))
for y in range(1180, H):                   # 底部渐变
    t = (y - 1180) / (H - 1180)
    a = int(218 * t ** 1.35)
    gd.line([(0, y), (W, y)], fill=(3, 6, 12, a))
im = Image.alpha_composite(im, grad)

# ---------- 2. 轻微暗角（电影感） ----------
mask = Image.new("L", (W, H), 0)
md = ImageDraw.Draw(mask)
md.ellipse([-W * 0.28, -H * 0.16, W * 1.28, H * 1.16], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(160))
inv = ImageOps_invert = Image.eval(mask, lambda v: 255 - v)
vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
vig.putalpha(inv.point(lambda v: int(v * 0.32)))
im = Image.alpha_composite(im, vig)

# ---------- 3. 文字工具（柔光阴影 + 描边感） ----------
def draw_glow_text(base, xy, txt, font, fill, anchor="mm",
                   shadow=(0, 0, 0), blur=10, s_alpha=230):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text(xy, txt, font=font, fill=shadow + (s_alpha,), anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)
    d = ImageDraw.Draw(base)
    d.text(xy, txt, font=font, fill=fill + (255,), anchor=anchor)

F_HEI = r"C:\Windows\Fonts\simhei.ttf"      # 黑体（大标题更有力）
F_YA = r"C:\Windows\Fonts\msyhbd.ttc"       # 雅黑粗体
f_badge_top = ImageFont.truetype(F_YA, 40)
f_brand     = ImageFont.truetype(F_HEI, 178)
f_chap_tag  = ImageFont.truetype(F_YA, 46)
f_title     = ImageFont.truetype(F_HEI, 138)
f_hook      = ImageFont.truetype(F_YA, 47)

# ---------- 4. 顶部品牌区 ----------
draw_glow_text(im, (540, 132), "职 场 悬 疑 · 连 载 短 篇",
               f_badge_top, (208, 220, 232), blur=6, s_alpha=200)
draw_glow_text(im, (540, 305), "偏 差", f_brand, WHITE,
               blur=14, s_alpha=240)
# 书名下红色短线装饰
dd = ImageDraw.Draw(im)
dd.rounded_rectangle([440, 420, 640, 430], radius=5, fill=RED + (235,))

# ---------- 5. 底部章节区 ----------
# 红色「第五章」徽标
tag_w, tag_h = 196, 66
tx0, ty0 = 540 - tag_w // 2, 1420
dd.rounded_rectangle([tx0, ty0, tx0 + tag_w, ty0 + tag_h],
                     radius=12, fill=RED + (242,))
dd.text((540, ty0 + tag_h // 2 - 2), "第 五 章",
        font=f_chap_tag, fill=WHITE + (255,), anchor="mm")

# 章节主标题
draw_glow_text(im, (540, 1572), "工牌上的脸", f_title, WHITE,
               blur=13, s_alpha=245)

# 钩子文案两行（关键词用暖红点亮）
hook1 = "工牌照片里的人，老了二十岁，"
hook2 = "却穿着他今天刚换的衬衫。"
def draw_hook_line(y, parts):
    """parts: [(text, is_red)] 居中排版多色一行"""
    total = sum(dd.textlength(t, font=f_hook) for t, _ in parts)
    x = 540 - total / 2
    for t, is_red in parts:
        col = (238, 106, 92) if is_red else SOFT
        draw_glow_text(im, (x, y), t, f_hook, col,
                       anchor="lm", blur=6, s_alpha=210)
        x += dd.textlength(t, font=f_hook)

draw_hook_line(1712, [("工牌照片里的人，", False), ("老了二十岁", True), ("，", False)])
draw_hook_line(1790, [("却穿着他", False), ("今天刚换的衬衫", True), ("。", False)])

# ---------- 6. 输出 ----------
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
final = im.convert("RGB")
final.save(OUT_PNG)
final.save(OUT_JPG, quality=92)
print("PNG:", OUT_PNG, os.path.getsize(OUT_PNG), "bytes")
print("JPG:", OUT_JPG, os.path.getsize(OUT_JPG), "bytes")
