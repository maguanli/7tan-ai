# -*- coding: utf-8 -*-
"""7Tan LOGO v4：v3a 的 t 改为大写 T（7Tan），其余完全保持 v3a 设计"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------- 采样 logo_1024.png 渐变起止色（与 v3 相同）----------
src = Image.open(os.path.join(BASE, "logo_1024.png")).convert("RGB")
W, H = src.size
top_color = src.getpixel((W // 2, 30))
bottom_color = src.getpixel((W // 2, H - 30))
print(f"采样渐变: 顶部 {top_color} -> 底部 {bottom_color}")

def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def make_gradient(size, c_top, c_bottom):
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=lerp(c_top, c_bottom, y / size))
    hl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse([size * 0.15, -size * 0.25, size * 0.85, size * 0.35],
               fill=(255, 255, 255, 60))
    hl = hl.filter(ImageFilter.GaussianBlur(size // 8))
    return Image.alpha_composite(img.convert("RGBA"), hl)

def round_corner(img, radius):
    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out

def draw_glow_text(img, text, font_path, font_size):
    size = img.size[0]
    txt = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    font = ImageFont.truetype(font_path, font_size)
    td.text((size // 2, size // 2), text, font=font,
            fill=(255, 255, 255, 255), anchor="mm")
    glow_far = txt.filter(ImageFilter.GaussianBlur(size // 28))
    glow_near = txt.filter(ImageFilter.GaussianBlur(size // 60))
    img = Image.alpha_composite(img, glow_far)
    img = Image.alpha_composite(img, glow_near)
    img = Image.alpha_composite(img, txt)
    return img

font_candidates = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
font_path = next((p for p in font_candidates if os.path.exists(p)), None)
print(f"字体: {font_path}")

SIZE = 1024
img = make_gradient(SIZE, top_color, bottom_color)
img = draw_glow_text(img, "7Tan", font_path, 400)
img = round_corner(img, 180)
for out_size in (1024, 512, 256):
    out = img.resize((out_size, out_size), Image.LANCZOS)
    path = os.path.join(BASE, f"logo_v4_{out_size}.png")
    out.save(path)
    print(f"已生成: {path}")
print("全部完成")
