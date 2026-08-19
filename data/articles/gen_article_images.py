# -*- coding: utf-8 -*-
"""为《公众号爆款拆解》文章生成 6 张定制配图（全新生成，非旧图）"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = "data/articles/images_v3"
os.makedirs(OUT, exist_ok=True)

# ---------- 字体 ----------
F_TITLE = "C:/Windows/Fonts/msyhbd.ttc"   # 微软雅黑粗体
F_BODY  = "C:/Windows/Fonts/msyh.ttc"    # 微软雅黑常规
F_HEI   = "C:/Windows/Fonts/simhei.ttf"  # 黑体

def font(path, size):
    return ImageFont.truetype(path, size)

# ---------- 配色 ----------
BG       = (24, 26, 32)     # 深色底
BG2      = (32, 35, 44)     # 次级底
ACCENT   = (232, 92, 58)    # 橙色
GOLD     = (240, 180, 70)   # 金色
WHITE    = (245, 245, 245)
GRAY     = (160, 165, 175)
GREEN    = (80, 190, 120)
BLUE     = (90, 150, 230)

def rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)

def text_c(draw, cx, y, s, fnt, fill):
    """水平居中绘制文本"""
    w = draw.textlength(s, font=fnt)
    draw.text((cx - w/2, y), s, font=fnt, fill=fill)
    return w

def draw_gradient(size, c1, c2):
    w, h = size
    img = Image.new("RGB", size, c1)
    px = img.load()
    for x in range(w):
        t = x / w
        r = int(c1[0] + (c2[0]-c1[0])*t)
        g = int(c1[1] + (c2[1]-c1[1])*t)
        b = int(c1[2] + (c2[2]-c1[2])*t)
        for y in range(h):
            px[x, y] = (r, g, b)
    return img

def base(w=1080, h=608):
    return draw_gradient((w, h), (26, 28, 36), (18, 19, 25))

# ========== 1. 封面卡 900x383 ==========
img = base(900, 383)
d = ImageDraw.Draw(img)
f_small = font(F_BODY, 22)
f_mid   = font(F_TITLE, 34)
f_big   = font(F_TITLE, 46)
f_sub   = font(F_BODY, 26)
# 左侧色条
d.rectangle([0, 0, 8, 383], fill=ACCENT)
# 小标签
rounded(d, (40, 36, 200, 72), 18, (232, 92, 58))
text_c(d, 120, 42, "公众号爆款拆解", f_small, WHITE)
# 主标题
text_c(d, 450, 110, "3000+ 阅读的爆款", f_big, WHITE)
text_c(d, 450, 175, "是怎么写出来的？", f_big, WHITE)
# 副标题引用
rounded(d, (60, 240, 840, 310), 16, BG2)
text_c(d, 450, 252, "拆解：《李亚鹏：欠4000万被强制执行，最后靠“做慈善”翻了身》", f_sub, GOLD)
# 底部
text_c(d, 450, 340, "老马 · 拆解手记", f_small, GRAY)
img.save(f"{OUT}/v3_cover.png", quality=92)
print("cover ok")

# ========== 2. 标题公式图 1080x608 ==========
img = base()
d = ImageDraw.Draw(img)
text_c(d, 540, 40, "拆一篇3000+爆款，先拆标题", f_mid, WHITE)
blocks = [("名人", "李亚鹏", ACCENT), ("数字", "4000万", GOLD), ("冲突", "被强制执行", BLUE), ("反转", "做慈善翻身", GREEN)]
bw, bh = 200, 150
total_w = bw*4 + 60*3
x0 = (1080 - total_w) // 2
y0 = 150
for i, (k, v, c) in enumerate(blocks):
    x = x0 + i*(bw+60)
    rounded(d, (x, y0, x+bw, y0+bh), 18, (c[0]//3, c[1]//3, c[2]//3))
    d.rectangle([x, y0, x+bw, y0+8], fill=c)
    text_c(d, x+bw/2, y0+30, k, font(F_BODY, 26), c)
    text_c(d, x+bw/2, y0+78, v, font(F_TITLE, 36), WHITE)
    if i < 3:
        d.text((x+bw+14, y0+55), "+", font=font(F_TITLE, 40), fill=GRAY)
# 等号 + 结果
d.text((x0+total_w/2-30, y0+bh+30), "=", font=font(F_TITLE, 44), fill=WHITE)
rounded(d, (x0+160, y0+bh+90, x0+total_w-160, y0+bh+160), 16, ACCENT)
text_c(d, 540, y0+bh+106, "打开率直接翻倍", font(F_TITLE, 32), WHITE)
# 底部注释
text_c(d, 540, 545, "没有数字、没有冲突的标题，别人扫一眼就划走了", font(F_BODY, 24), GRAY)
img.save(f"{OUT}/v3_formula_title.png", quality=92)
print("formula_title ok")

# ========== 3. 黄金开头图 1080x608 ==========
img = base()
d = ImageDraw.Draw(img)
text_c(d, 540, 40, "再看开头第一句：黄金三秒", f_mid, WHITE)
# 引用框
rounded(d, (90, 120, 990, 250), 20, BG2)
d.rectangle([90, 120, 104, 250], fill=GOLD)
d.text((140, 145), "“", font=font(F_TITLE, 60), fill=GOLD)
d.text((180, 155), "李亚鹏，又上热搜了。", font=font(F_TITLE, 40), fill=WHITE)
text_c(d, 540, 215, "—— 原文开头（一句话就吊住胃口）", font(F_BODY, 22), GRAY)
# 点评
items = [
    ("01", "蹭热点：主角自带话题，读者想点", GOLD),
    ("02", "悬念：为什么又？之前怎么了？", BLUE),
    ("03", "短句：7个字读完，不费脑", GREEN),
]
y = 290
for num, txt, c in items:
    rounded(d, (110, y, 970, y+76), 14, (40, 44, 56))
    d.ellipse([130, y+18, 166, y+54], fill=c)
    text_c(d, 148, y+22, num, font(F_TITLE, 24), (20, 20, 20))
    d.text((190, y+20), txt, font=font(F_BODY, 28), fill=WHITE)
    y += 94
img.save(f"{OUT}/v3_golden_open.png", quality=92)
print("golden_open ok")

# ========== 4. 过山车结构图 1080x608 ==========
img = base()
d = ImageDraw.Draw(img)
text_c(d, 540, 36, "故事结构：过山车", f_mid, WHITE)
text_c(d, 540, 92, "高光 → 低谷 → 救赎，情绪一路向上", font(F_BODY, 24), GRAY)
# 画曲线
pts = [(90, 470), (300, 180), (540, 430), (780, 160), (990, 400)]
d.line(pts, fill=ACCENT, width=6, joint="curve")
# 节点
labels = [("高光", "舞台上举奖杯", 300), ("低谷", "欠4000万被追债", 540), ("救赎", "做慈善翻身", 780)]
for name, desc, x in labels:
    idx = [p[0] for p in pts].index(x)
    y = pts[idx][1]
    d.ellipse([x-14, y-14, x+14, y+14], fill=GOLD)
    d.ellipse([x-8, y-8, x+8, y+8], fill=(250, 230, 180))
    text_c(d, x, y+26, name, font(F_TITLE, 30), GOLD)
    text_c(d, x, y+64, desc, font(F_BODY, 22), WHITE)
# 底部说明
rounded(d, (120, 520, 960, 578), 14, BG2)
text_c(d, 540, 530, "读者情绪被一次次拉起来，就一直看到底", font(F_BODY, 24), GRAY)
img.save(f"{OUT}/v3_roller.png", quality=92)
print("roller ok")

# ========== 5. 爆款公式总图 1080x608 ==========
img = base()
d = ImageDraw.Draw(img)
text_c(d, 540, 36, "爆款 = 六件套", f_mid, WHITE)
items = [
    ("猎奇标题", "名人+数字+冲突+反转"),
    ("黄金开头", "第一句就吊住胃口"),
    ("过山车结构", "高光-低谷-救赎"),
    ("细节画面", "让人物立起来"),
    ("金句升华", "给读者转发理由"),
    ("互动结尾", "让评论区自己长出来"),
]
# 2列3行
cw, ch = 420, 130
x0, y0 = (1080 - cw*2 - 40)//2, 100
for i, (t, s) in enumerate(items):
    x = x0 + (i % 2) * (cw + 40)
    y = y0 + (i // 2) * (ch + 30)
    rounded(d, (x, y, x+cw, y+ch), 16, (38, 42, 54))
    d.rectangle([x, y, x+10, y+ch], fill=ACCENT)
    text_c(d, x+cw/2, y+18, t, font(F_TITLE, 30), WHITE)
    text_c(d, x+cw/2, y+72, s, font(F_BODY, 22), GRAY)
img.save(f"{OUT}/v3_formula_total.png", quality=92)
print("formula_total ok")

# ========== 6. 金句卡 1080x608 ==========
img = base()
d = ImageDraw.Draw(img)
rounded(d, (70, 60, 1010, 548), 28, (36, 30, 40))
d.rectangle([70, 60, 1010, 70], fill=GOLD)
text_c(d, 540, 110, "金句 · 给读者一个转发的理由", font(F_BODY, 24), GOLD)
text_c(d, 540, 190, "输掉面子，", font(F_TITLE, 64), WHITE)
text_c(d, 540, 290, "守住里子。", font(F_TITLE, 64), WHITE)
d.text((330, 420), "—— 全文最破防的一句", font=font(F_BODY, 24), fill=GRAY)
text_c(d, 540, 500, "金句要短、要狠、要能被人截图转发", font(F_BODY, 22), GRAY)
img.save(f"{OUT}/v3_quote.png", quality=92)
print("quote ok")

print("ALL_DONE ->", OUT)
