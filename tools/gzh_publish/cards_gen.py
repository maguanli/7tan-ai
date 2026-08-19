# -*- coding: utf-8 -*-
"""
cards_gen.py — 为《大起大落的一生》文章生成配图
6 张正文金句卡片（1080x608）+ 1 张封面（900x383）
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

OUT = Path(r"D:\7tan\7tanAI\data\screenshots\gzh_cards")
OUT.mkdir(parents=True, exist_ok=True)

# ---------- 字体 ----------
def find_font(size, bold=False):
    candidates = []
    if bold:
        candidates += [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf"]
    candidates += [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                   r"C:\Windows\Fonts\simsun.ttc"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ---------- 渐变背景 ----------
def gradient_bg(w, h, c1, c2):
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    return base.resize((w, h))


# ---------- 装饰圆 ----------
def add_circles(img, alpha=28):
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    import random
    random.seed(7)
    for _ in range(6):
        r = random.randint(80, 260)
        x = random.randint(-100, w - 100)
        y = random.randint(-100, h - 100)
        d.ellipse([x, y, x + r, y + r], fill=(255, 255, 255, alpha))
    return img


# ---------- 多行居中文字 ----------
def draw_center(d, img_w, y, text, font, fill, line_gap=18):
    lines = text.split("\n")
    total_h = len(lines) * (font.size + line_gap) - line_gap
    y = y - total_h // 2
    for ln in lines:
        bbox = d.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        d.text(((img_w - tw) / 2 - bbox[0], y - bbox[1]), ln, font=font, fill=fill)
        y += font.size + line_gap


def make_card(filename, badge, quote, sub="—— 大起大落的一生 ——", theme="blue"):
    W, H = 1080, 608
    themes = {
        "blue": ((18, 42, 92), (52, 96, 168)),      # 深蓝→蓝
        "green": ((10, 58, 48), (34, 138, 110)),    # 墨绿→青
        "orange": ((110, 48, 12), (210, 120, 40)),  # 暖橙
        "purple": ((58, 20, 90), (128, 68, 168)),   # 深紫→紫
        "dark": ((20, 26, 46), (58, 74, 120)),      # 深夜蓝
    }
    c1, c2 = themes.get(theme, themes["blue"])
    img = gradient_bg(W, H, c1, c2)
    img = add_circles(img)
    d = ImageDraw.Draw(img)

    # 顶部章节徽标
    f_badge = find_font(34, bold=True)
    bbox = d.textbbox((0, 0), badge, font=f_badge)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bx, by = (W - bw) // 2 - bbox[0], 96 - bbox[1]
    # 徽标底
    pad = 26
    d.rounded_rectangle([bx - pad, by - 14, bx + bw + pad, by + bh + 14],
                        radius=30, fill=(255, 255, 255, 40), outline=(255, 255, 255, 120), width=2)
    d.text((bx, by), badge, font=f_badge, fill=(255, 255, 255, 255))

    # 金句（自动换行）
    f_quote = find_font(52, bold=True)
    wrapped = []
    cur = ""
    for ch in quote:
        test = cur + ch
        bbox = d.textbbox((0, 0), test, font=f_quote)
        if bbox[2] - bbox[0] > W - 220 and cur:
            wrapped.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        wrapped.append(cur)
    quote_text = "\n".join(wrapped)
    draw_center(d, W, 320, quote_text, f_quote, (255, 255, 255, 255), line_gap=22)

    # 分隔线
    d.line([W // 2 - 90, 470, W // 2 + 90, 470], fill=(255, 255, 255, 150), width=2)

    # 底部署名
    f_sub = find_font(30)
    draw_center(d, W, 520, sub, f_sub, (255, 255, 255, 200))

    path = OUT / filename
    img.save(path, quality=92)
    print("SAVED", path)


def make_cover():
    W, H = 900, 383
    img = gradient_bg(W, H, (16, 36, 84), (66, 120, 190))
    img = add_circles(img, alpha=32)
    d = ImageDraw.Draw(img)

    f_big = find_font(56, bold=True)
    text = "40岁才明白\n人生最好的活法是这四个字"
    draw_center(d, W, H // 2 - 10, text, f_big, (255, 255, 255, 255), line_gap=12)

    f_small = find_font(24)
    draw_center(d, W, H - 44, "大起大落的一生", f_small, (255, 255, 255, 210))

    path = OUT / "cover_900x383.png"
    img.save(path, quality=92)
    print("SAVED", path)


if __name__ == "__main__":
    cards = [
        ("card_00_open.png", "卷首语", "我们总以为，人生是一条越走越宽的路。\n可真正活过的人才明白——人生更像坐过山车。", "blue"),
        ("card_01_fa.png", "01 讲个我发小的故事", "顺境时别得意忘形，逆境时别自暴自弃。\n真正的强者，不是没有低谷，\n而是从谷底爬出来时，还带着笑。", "orange"),
        ("card_02_ayi.png", "02 讲个我邻居阿姨的故事", "低谷时最该做的，不是抱怨，\n而是闭嘴、存钱、读书、锻炼。\n等你把低谷的日子过成了规律，\n抬头那天，天已经亮了。", "green"),
        ("card_03_self.png", "03 讲讲我自己", "锦上添花的人很多，雪中送炭的人很少。\n留在你身边的人，才是你这辈子最大的财富。", "purple"),
        ("card_04_10s.png", "送给低谷中的你", "别高估一年能做成的事，\n别低估十年能做成的事。\n这一切，都会过去。", "dark"),
        ("card_05_end.png", "写在最后", "人生就像四季，冬去春会来。\n熬过最冷的那段日子，\n花开的时候，一定格外好看。", "blue"),
    ]
    for fn, badge, quote, theme in cards:
        make_card(fn, badge, quote, theme=theme)
    make_cover()
    print("ALL DONE")
