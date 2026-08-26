# -*- coding: utf-8 -*-
"""
公众号 LOGO 专业绘制（本地 PIL，零成本，美观+含义兼顾）
「大起大落的一生」—— 圆形徽章式设计
方案A 星辉之路：深蓝渐变圆底 + 金色人生曲线 + 登顶小人 + 谷底金星
方案B 旭日人生：暖橙渐变圆底 + 双峰登顶 + 旗帜小人 + 太阳
超采样 4x 抗锯齿 → 800x800 / 360x360
"""
import os
import math
from PIL import Image, ImageDraw, ImageFilter

OUT = r"D:\7tan\7tanAI\data\logo"
os.makedirs(OUT, exist_ok=True)

SS = 4          # 超采样倍数
SIZE = 800      # 输出尺寸
BIG = SIZE * SS  # 绘制画布


def radial_gradient(size, top_color, bottom_color):
    """垂直径向渐变（顶部→底部），返回 RGBA 图像"""
    img = Image.new("RGB", (size, size), top_color)
    d = ImageDraw.Draw(img)
    w, h = size, size
    for y in range(h):
        t = y / (h - 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def bezier_points(p0, p1, p2, p3, n=120):
    """三次贝塞尔曲线采样点"""
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def draw_star(d, cx, cy, r_outer, r_inner, n=5, rot=-math.pi / 2, fill=(255, 215, 0)):
    """五角星"""
    pts = []
    for i in range(n * 2):
        ang = rot + i * math.pi / n
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    d.polygon(pts, fill=fill)


def draw_person(d, x, y, scale, color=(255, 255, 255), arm_up=True):
    """简约卡通小人：圆头 + 身体 + 张开双臂 + 双腿"""
    r = 26 * scale            # 头半径
    # 头
    d.ellipse([x - r, y - r * 2.4, x + r, y - r * 0.4], fill=color)
    # 身体
    d.rounded_rectangle([x - r * 0.9, y - r * 0.3, x + r * 0.9, y + r * 1.6],
                        radius=r * 0.4, fill=color)
    # 双臂（张开）
    if arm_up:
        d.line([(x - r * 0.8, y + r * 0.1), (x - r * 2.6, y - r * 1.4)],
               fill=color, width=int(8 * scale))
        d.line([(x + r * 0.8, y + r * 0.1), (x + r * 2.6, y - r * 1.4)],
               fill=color, width=int(8 * scale))
    else:
        d.line([(x - r * 0.8, y + r * 0.1), (x - r * 2.6, y + r * 1.3)],
               fill=color, width=int(8 * scale))
        d.line([(x + r * 0.8, y + r * 0.1), (x + r * 2.6, y + r * 1.3)],
               fill=color, width=int(8 * scale))
    # 双腿
    d.line([(x - r * 0.4, y + r * 1.5), (x - r * 1.2, y + r * 2.7)],
           fill=color, width=int(9 * scale))
    d.line([(x + r * 0.4, y + r * 1.5), (x + r * 1.2, y + r * 2.7)],
           fill=color, width=int(9 * scale))


def glow(d, cx, cy, radius, color, alpha=90, steps=24):
    """柔和光晕（多层半透明圆）"""
    for i in range(steps, 0, -1):
        rr = int(radius * i / steps)
        a = int(alpha * (1 - i / steps) ** 1.6)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color[:3] + (a,))


def make_a():
    """方案A 星辉之路：深蓝渐变 + 金色曲线 + 登顶小人 + 谷底金星"""
    img = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    # 圆形渐变底（深蓝夜空 → 深靛蓝）
    grad = radial_gradient(BIG, (18, 28, 66), (8, 12, 34)).convert("RGBA")
    mask = Image.new("L", (BIG, BIG), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, BIG - 1, BIG - 1], fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img, "RGBA")
    c = BIG / 2

    # 背景细环装饰
    d.ellipse([c - c * 0.96, c - c * 0.96, c + c * 0.96, c + c * 0.96],
              outline=(255, 215, 120, 60), width=int(BIG * 0.004))

    # 谷底金星（左下）+ 光晕
    star_x, star_y = c - BIG * 0.30, c + BIG * 0.22
    glow(d, star_x, star_y, BIG * 0.10, (255, 200, 80, 0), alpha=80)
    draw_star(d, star_x, star_y, BIG * 0.055, BIG * 0.024, fill=(255, 215, 120, 255))

    # 点缀小星星（右上）
    dots = [(c + BIG * 0.30, c - BIG * 0.30), (c + BIG * 0.10, c - BIG * 0.42),
            (c + BIG * 0.38, c - BIG * 0.08), (c - BIG * 0.38, c - BIG * 0.20)]
    for sx, sy in dots:
        draw_star(d, sx, sy, BIG * 0.016, BIG * 0.007, fill=(255, 235, 180, 200))

    # 金色人生曲线（左下低谷 → 中部起伏 → 右上顶峰）贝塞尔拼接
    curve = []
    curve += bezier_points((c - BIG * 0.36, c + BIG * 0.34),
                           (c - BIG * 0.18, c + BIG * 0.30),
                           (c - BIG * 0.16, c + BIG * 0.02),
                           (c - BIG * 0.02, c + BIG * 0.00), 80)
    curve += bezier_points((c - BIG * 0.02, c + BIG * 0.00),
                           (c + BIG * 0.14, c - BIG * 0.02),
                           (c + BIG * 0.12, c - BIG * 0.30),
                           (c + BIG * 0.26, c - BIG * 0.30), 80)
    # 画曲线（多层：外发光 + 主体）
    d.line(curve, fill=(255, 190, 70, 90), width=int(BIG * 0.035))
    d.line(curve, fill=(255, 215, 120, 255), width=int(BIG * 0.020))

    # 顶峰小人（站在曲线最高点附近）+ 光晕
    px, py = c + BIG * 0.26, c - BIG * 0.24
    glow(d, px, py, BIG * 0.09, (255, 255, 255, 0), alpha=60)
    draw_person(d, px, py, BIG / 800 * 1.0, color=(255, 255, 255, 255))

    # 底部弧线文字区留白 + 顶部小光点
    d.ellipse([c - BIG * 0.02, c - BIG * 0.44, c + BIG * 0.02, c - BIG * 0.40],
              fill=(255, 240, 200, 230))

    # 外圈金环
    d.ellipse([c - c * 0.985, c - c * 0.985, c + c * 0.985, c + c * 0.985],
              outline=(255, 215, 120, 180), width=int(BIG * 0.010))
    return img


def make_b():
    """方案B 旭日人生：暖橙渐变 + 双峰登顶 + 旗帜小人"""
    img = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    # 圆形渐变底（暖橙 → 米白）
    grad = radial_gradient(BIG, (255, 176, 92), (255, 235, 205)).convert("RGBA")
    mask = Image.new("L", (BIG, BIG), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, BIG - 1, BIG - 1], fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img, "RGBA")
    c = BIG / 2

    # 太阳（右上）+ 光晕
    sun_x, sun_y = c + BIG * 0.30, c - BIG * 0.30
    glow(d, sun_x, sun_y, BIG * 0.11, (255, 255, 255, 0), alpha=110)
    d.ellipse([sun_x - BIG * 0.07, sun_y - BIG * 0.07,
               sun_x + BIG * 0.07, sun_y + BIG * 0.07], fill=(255, 245, 220, 255))

    # 低山（左）+ 高山（右）剪影
    low_pts = [(c - BIG * 0.48, c + BIG * 0.20), (c - BIG * 0.28, c - BIG * 0.10),
               (c - BIG * 0.10, c + BIG * 0.20)]
    high_pts = [(c - BIG * 0.18, c + BIG * 0.20), (c + BIG * 0.22, c - BIG * 0.34),
                (c + BIG * 0.46, c + BIG * 0.20)]
    d.polygon(low_pts, fill=(120, 90, 60, 255))
    d.polygon(high_pts, fill=(90, 65, 45, 255))
    # 山体高光（右侧受光面，柔和不突兀）
    d.polygon([(c - BIG * 0.02, c + BIG * 0.20), (c + BIG * 0.22, c - BIG * 0.34),
               (c + BIG * 0.46, c + BIG * 0.20)], fill=(128, 96, 66, 255))

    # 山顶旗帜
    fx, fy = c + BIG * 0.22, c - BIG * 0.34
    d.line([(fx, fy), (fx, fy - BIG * 0.14)], fill=(70, 50, 35, 255), width=int(BIG * 0.010))
    d.polygon([(fx, fy - BIG * 0.14), (fx + BIG * 0.09, fy - BIG * 0.105),
               (fx, fy - BIG * 0.07)], fill=(255, 90, 70, 255))

    # 起点橙点（左下谷底）
    d.ellipse([c - BIG * 0.42 - BIG * 0.03, c + BIG * 0.14 - BIG * 0.03,
               c - BIG * 0.42 + BIG * 0.03, c + BIG * 0.14 + BIG * 0.03],
              fill=(255, 140, 60, 255))

    # 路径虚线（谷底 → 顶峰）
    path = bezier_points((c - BIG * 0.42, c + BIG * 0.14),
                         (c - BIG * 0.30, c + BIG * 0.06),
                         (c - BIG * 0.12, c - BIG * 0.16),
                         (c + BIG * 0.16, c - BIG * 0.28), 100)
    step = 8
    for i in range(0, len(path) - step, step * 2):
        d.line([path[i], path[min(i + step, len(path) - 1)]],
               fill=(255, 255, 255, 200), width=int(BIG * 0.012))

    # 外圈环
    d.ellipse([c - c * 0.985, c - c * 0.985, c + c * 0.985, c + c * 0.985],
              outline=(255, 255, 255, 170), width=int(BIG * 0.010))
    return img


def finalize(img, name):
    """缩小 + 圆角掩膜 + 保存"""
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    # 圆形掩膜（圆角头像效果）
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out.save(os.path.join(OUT, name))
    # 360 版本
    out.resize((360, 360), Image.LANCZOS).save(os.path.join(OUT, name.replace(".png", "_360.png")))
    print("[OK]", name, "-> 800/360 saved")


if __name__ == "__main__":
    finalize(make_a(), "logo_final_A.png")
    finalize(make_b(), "logo_final_B.png")
    print("done. open preview.html")
