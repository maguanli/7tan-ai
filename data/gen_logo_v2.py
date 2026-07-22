# -*- coding: utf-8 -*-
"""生成 7tan LOGO 两版：AI元素版 / 简洁版
要求：仅含 "7tan" 字符、结构简洁、颜色柔和
"""
import os
import random
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT_DIR = r"data\logo"
os.makedirs(OUT_DIR, exist_ok=True)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
]


def get_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size), os.path.basename(p)
            except Exception:
                continue
    return ImageFont.load_default(), "default"


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_bg(size, c_top, c_bottom):
    img = Image.new("RGB", (size, size), c_top)
    d = ImageDraw.Draw(img)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=lerp(c_top, c_bottom, y / (size - 1)))
    return img


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    try:
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    except Exception:
        d.rectangle([0, 0, size - 1, size - 1], fill=255)
    return m


def draw_centered_text(base, text, font, fill, glow_color=None, glow_radius=0, glow_alpha=180):
    size = base.size[0]
    tmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    bbox = td.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size - w) // 2 - bbox[0]
    y = (size - h) // 2 - bbox[1]
    if glow_color and glow_radius:
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.text((x, y), text, font=font, fill=glow_color + (glow_alpha,))
        glow = glow.filter(ImageFilter.GaussianBlur(glow_radius))
        base.alpha_composite(glow)
    d2 = ImageDraw.Draw(base)
    d2.text((x, y), text, font=font, fill=fill)


def version_ai(size=1024):
    """AI 元素版：柔和蓝紫渐变 + 神经网络节点连线 + 文字微光"""
    random.seed(42)
    img = gradient_bg(size, (176, 196, 231), (216, 190, 233)).convert("RGBA")
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)

    # 神经节点（避开中央文字区）
    nodes = []
    cx = cy = size / 2
    for _ in range(16):
        for _try in range(50):
            x = random.uniform(size * 0.08, size * 0.92)
            y = random.uniform(size * 0.08, size * 0.92)
            if abs(x - cx) < size * 0.42 and abs(y - cy) < size * 0.16:
                continue
            nodes.append((x, y))
            break

    def dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    # 近邻连线（低透明度，保持柔和）
    for a in nodes:
        near = sorted((b for b in nodes if b is not a), key=lambda b: dist(a, b))[:3]
        for b in near:
            if dist(a, b) < size * 0.33:
                ld.line([a, b], fill=(255, 255, 255, 70), width=max(2, size // 400))

    # 普通节点
    for (x, y) in nodes:
        r = random.uniform(size * 0.006, size * 0.012)
        ld.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 150))

    # 3 个 hub 节点带光晕
    for (x, y) in random.sample(nodes, 3):
        r = size * 0.014
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2], fill=(255, 255, 255, 90))
        glow = glow.filter(ImageFilter.GaussianBlur(size * 0.012))
        layer.alpha_composite(glow)
        ld.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 220))

    img.alpha_composite(layer)

    font, used = get_font(int(size * 0.30))
    draw_centered_text(img, "7tan", font, (255, 255, 255, 255),
                       glow_color=(255, 255, 255), glow_radius=size * 0.03, glow_alpha=200)
    return img, used


def version_clean(size=1024):
    """简洁版：莫兰迪青米渐变 + 深石灰文字，无任何 AI 元素"""
    img = gradient_bg(size, (214, 226, 222), (243, 230, 221)).convert("RGBA")
    font, used = get_font(int(size * 0.30))
    draw_centered_text(img, "7tan", font, (74, 85, 104, 255))
    return img, used


def save_all(img, name):
    for s in (1024, 512, 256):
        im = img if img.size[0] == s else img.resize((s, s), Image.LANCZOS)
        final = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        final.paste(im, (0, 0), rounded_mask(s, int(s * 0.22)))
        final.save(os.path.join(OUT_DIR, f"{name}_{s}.png"))


if __name__ == "__main__":
    a, fa = version_ai()
    save_all(a, "logo_ai")
    print("AI版字体:", fa)
    b, fb = version_clean()
    save_all(b, "logo_clean")
    print("简洁版字体:", fb)
    print("done ->", os.path.abspath(OUT_DIR))
