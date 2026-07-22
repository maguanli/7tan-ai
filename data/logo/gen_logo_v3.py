# -*- coding: utf-8 -*-
"""7tan LOGO v3：logo_1024.png 的蓝紫渐变背景 + logo_ai_1024.png 的柔光字体"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------- 1. 采样 logo_1024.png 的渐变起止色 ----------
src = Image.open(os.path.join(BASE, "logo_1024.png")).convert("RGB")
W, H = src.size
top_color = src.getpixel((W // 2, 30))          # 顶部中心
bottom_color = src.getpixel((W // 2, H - 30))   # 底部中心
print(f"采样渐变: 顶部 {top_color} -> 底部 {bottom_color}")

# ---------- 2. 工具函数 ----------
def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def make_gradient(size, c_top, c_bottom):
    """垂直渐变底图（含顶部柔和高光，还原 logo_1024 风格）"""
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=lerp(c_top, c_bottom, y / size))
    # 顶部柔光（椭圆白色半透明，大模糊）
    hl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse([size * 0.15, -size * 0.25, size * 0.85, size * 0.35],
               fill=(255, 255, 255, 60))
    hl = hl.filter(ImageFilter.GaussianBlur(size // 8))
    img = Image.alpha_composite(img.convert("RGBA"), hl)
    return img

def round_corner(img, radius):
    """圆角遮罩"""
    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, img.size[0], img.size[1]],
                         radius=radius, fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out

def draw_glow_text(img, text, font_path, font_size):
    """白色柔光文字（logo_ai 风格）：多层模糊光晕 + 实心字"""
    size = img.size[0]
    txt = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    font = ImageFont.truetype(font_path, font_size)
    td.text((size // 2, size // 2), text, font=font,
            fill=(255, 255, 255, 255), anchor="mm")
    # 柔光：两层模糊叠加
    glow_far = txt.filter(ImageFilter.GaussianBlur(size // 28))
    glow_near = txt.filter(ImageFilter.GaussianBlur(size // 60))
    img = Image.alpha_composite(img, glow_far)
    img = Image.alpha_composite(img, glow_near)
    img = Image.alpha_composite(img, txt)
    return img

def draw_bubble(img, base_color):
    """右下角对话气泡（logo_1024 原版元素）：白色气泡 + 三个主题色圆点"""
    size = img.size[0]
    bub = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bub)
    # 气泡主体
    bx0, by0 = size * 0.58, size * 0.60
    bx1, by1 = size * 0.90, size * 0.80
    r = size * 0.06
    bd.rounded_rectangle([bx0, by0, bx1, by1], radius=r,
                         fill=(255, 255, 255, 235))
    # 小三角尾巴
    bd.polygon([(bx0 + size * 0.04, by1 - 2),
                (bx0 + size * 0.04, by1 + size * 0.07),
                (bx0 + size * 0.12, by1 - 2)],
               fill=(255, 255, 255, 235))
    # 三个圆点（用渐变底部色）
    dot_r = size * 0.022
    cy = (by0 + by1) / 2
    for i, cx in enumerate([bx0 + (bx1 - bx0) * 0.28,
                            bx0 + (bx1 - bx0) * 0.50,
                            bx0 + (bx1 - bx0) * 0.72]):
        bd.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                   fill=base_color + (255,))
    # 气泡微光
    bub_glow = bub.filter(ImageFilter.GaussianBlur(size // 80))
    img = Image.alpha_composite(img, bub_glow)
    img = Image.alpha_composite(img, bub)
    return img

# ---------- 3. 字体（与 logo_ai 同款 arialbd）----------
font_candidates = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
font_path = next((p for p in font_candidates if os.path.exists(p)), None)
print(f"字体: {font_path}")

# ---------- 4. 生成两个版本 ----------
SIZE = 1024
for tag, with_bubble in [("v3a", False), ("v3b", True)]:
    img = make_gradient(SIZE, top_color, bottom_color)
    img = draw_glow_text(img, "7tan", font_path, 400)
    if with_bubble:
        img = draw_bubble(img, bottom_color)
    img = round_corner(img, 180)
    for out_size in (1024, 512, 256):
        out = img.resize((out_size, out_size), Image.LANCZOS)
        path = os.path.join(BASE, f"logo_{tag}_{out_size}.png")
        out.save(path)
        print(f"已生成: {path}")
print("全部完成")
