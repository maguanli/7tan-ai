# -*- coding: utf-8 -*-
"""公众号LOGO专业绘制：渐变+贝塞尔+光晕+超采样抗锯齿，本地免费"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 3          # 超采样倍数(抗锯齿)
SIZE = 800
S = SIZE * SS
OUT = r"D:\7tan\7tanAI\data\logo"


def radial_circle_bg(inner, outer, center=(0.5, 0.45), edge_feather=10):
    """圆形径向渐变底(边缘透明)"""
    s = S
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float64)
    cx, cy = center[0] * s, center[1] * s
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (s * 0.72)
    d = np.clip(d, 0, 1)
    inner_c = np.array(inner, float)
    outer_c = np.array(outer, float)
    col = inner_c[None, None, :] * (1 - d[..., None]) + outer_c[None, None, :] * d[..., None]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    radius = 0.5 * s
    feather = edge_feather * SS
    mask = np.clip((radius - dist) / feather, 0, 1)
    arr = np.concatenate([col, mask[..., None] * 255], axis=-1).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def bezier_pts(pts, n=400):
    """连续三次贝塞尔采样, pts = [p0,c1,c2,p1,c1,c2,p2...]"""
    out = []
    for i in range(0, len(pts) - 3, 3):
        p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        t = np.linspace(0, 1, n)
        x = ((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] +
             3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0])
        y = ((1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] +
             3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1])
        for px, py in zip(x, y):
            out.append((px * S, py * S))
    return out


def draw_star(draw, cx, cy, R, r, color, rot=-90):
    pts = []
    for i in range(10):
        ang = math.radians(rot + i * 36)
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=color)


def person(draw, cx, cy, scale, color):
    """张开双臂卡通小人, cy=脚底"""
    u = SIZE * SS * 0.01 * scale
    r_head = 1.15 * u
    draw.line([cx, cy - 2.2 * u, cx - 0.8 * u, cy], fill=color, width=int(0.9 * u))
    draw.line([cx, cy - 2.2 * u, cx + 0.8 * u, cy], fill=color, width=int(0.9 * u))
    draw.rounded_rectangle([cx - 1.35 * u, cy - 4.6 * u, cx + 1.35 * u, cy - 2.2 * u],
                           radius=int(1.0 * u), fill=color)
    draw.line([cx - 1.35 * u, cy - 4.4 * u, cx - 3.0 * u, cy - 5.8 * u], fill=color, width=int(0.85 * u))
    draw.line([cx + 1.35 * u, cy - 4.4 * u, cx + 3.0 * u, cy - 5.8 * u], fill=color, width=int(0.85 * u))
    draw.ellipse([cx - r_head, cy - 6.6 * u - r_head, cx + r_head, cy - 6.6 * u + r_head], fill=color)


def glow(img, target, color, radius, alpha):
    """在img上叠加一个柔和光晕"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([target[0] - radius, target[1] - radius, target[0] + radius, target[1] + radius],
              fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.5))
    return Image.alpha_composite(img, layer)


def finalize(img, name):
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    img.save(OUT + "\\" + name)
    img.resize((360, 360), Image.LANCZOS).save(OUT + "\\" + name.replace(".png", "_360.png"))
    print("saved", name)


# ============ 方案A: 星辉曲线 (深蓝金·人生起伏) ============
def design_a():
    img = radial_circle_bg((44, 62, 100), (15, 21, 44), center=(0.5, 0.42))
    d = ImageDraw.Draw(img)
    gold = (226, 190, 106)
    pts = [(0.12, 0.84), (0.26, 0.52), (0.38, 0.70), (0.50, 0.50),
           (0.62, 0.30), (0.70, 0.46), (0.82, 0.30)]
    line_pts = bezier_pts(pts)
    # 曲线光晕
    d.line(line_pts, fill=gold + (60,), width=30 * SS)
    # 主曲线
    d.line(line_pts, fill=gold, width=12 * SS)
    # 低谷星星(带光晕)
    sx, sy = 0.345 * S, 0.765 * S
    img = glow(img, (sx, sy), (255, 214, 130), 46 * SS, 90)
    d = ImageDraw.Draw(img)
    draw_star(d, sx, sy, 17 * SS, 7 * SS, (255, 214, 130))
    # 波峰小人(白色+光晕)
    px, py = 0.82 * S, 0.30 * S
    img = glow(img, (px, py - 26 * SS), (220, 230, 255), 60 * SS, 70)
    d = ImageDraw.Draw(img)
    person(d, px, py, 1.35, (245, 248, 255))
    # 星光点缀
    rnd = np.random.RandomState(7)
    for _ in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(0.12, 0.40) * S
        cx0, cy0 = 0.5 * S + rr * math.cos(a), 0.42 * S + rr * math.sin(a)
        rad = rnd.uniform(1.5, 3.2) * SS
        alpha = int(rnd.uniform(50, 130))
        d.ellipse([cx0 - rad, cy0 - rad, cx0 + rad, cy0 + rad], fill=(255, 255, 255, alpha))
    finalize(img, "logo_v2_A.png")


# ============ 方案B: 旭日登峰 (暖橙·从低到高) ============
def design_b():
    img = radial_circle_bg((255, 168, 100), (192, 64, 64), center=(0.5, 0.52))
    # 圆日(柔和光晕)
    img = glow(img, (0.5 * S, 0.48 * S), (255, 240, 210), 120 * SS, 150)
    d = ImageDraw.Draw(img)
    d.ellipse([0.36 * S, 0.34 * S, 0.64 * S, 0.62 * S], fill=(255, 244, 220, 230))
    # 左山(低) 剪影
    left_ridge = [(0.02, 0.88), (0.12, 0.74), (0.24, 0.60), (0.34, 0.72), (0.42, 0.86)]
    left_poly = [(x * S, y * S) for x, y in left_ridge] + [(0.42 * S, S), (0.02 * S, S)]
    d.polygon(left_poly, fill=(255, 248, 240))
    # 右山(高) 剪影
    right_ridge = [(0.40, 0.92), (0.55, 0.70), (0.70, 0.44), (0.82, 0.58), (0.98, 0.76)]
    right_poly = [(x * S, y * S) for x, y in right_ridge] + [(0.98 * S, S), (0.40 * S, S)]
    d.polygon(right_poly, fill=(255, 248, 240))
    # 旗帜(深红)
    fx, fy = 0.70 * S, 0.44 * S
    d.line([fx, fy, fx, fy - 0.13 * S], fill=(178, 48, 48), width=4 * SS)
    d.polygon([(fx, fy - 0.13 * S), (fx + 0.11 * S, fy - 0.095 * S), (fx, fy - 0.06 * S)],
              fill=(196, 52, 52))
    # 飞鸟点缀
    for bx, by, sc in [(0.30, 0.40, 1.0), (0.78, 0.30, 0.8)]:
        w = 8 * SS * sc
        d.arc([bx * S - w, by * S - w * 0.6, bx * S, by * S + w * 0.6], 180, 360, fill=(255, 250, 240, 220), width=3 * SS)
        d.arc([bx * S, by * S - w * 0.6, bx * S + w, by * S + w * 0.6], 180, 360, fill=(255, 250, 240, 220), width=3 * SS)
    finalize(img, "logo_v2_B.png")


# ============ 方案C: 波浪人生 (浅色极简·现代) ============
def design_c():
    img = radial_circle_bg((249, 251, 255), (224, 232, 247), center=(0.5, 0.5))
    pts = [(0.16, 0.80), (0.30, 0.38), (0.46, 0.72), (0.60, 0.44), (0.72, 0.34), (0.82, 0.26)]
    line_pts = bezier_pts(pts, n=600)
    c1 = np.array([70, 130, 250])
    c2 = np.array([150, 90, 235])
    d = ImageDraw.Draw(img)
    # 渐变分段绘制(蓝->紫, 宽6->14)
    seg = 40
    for i in range(seg):
        a = i / seg
        col = tuple((c1 * (1 - a) + c2 * a).astype(int))
        w = int((6 + 8 * a) * SS)
        idx0 = int(i * (len(line_pts) - 1) / seg)
        idx1 = int((i + 1) * (len(line_pts) - 1) / seg)
        d.line(line_pts[idx0:idx1 + 1], fill=col, width=w)
    # 波峰小橙点(我)
    px, py = 0.82 * S, 0.26 * S - 30 * SS
    img = glow(img, (px, py), (255, 140, 80), 44 * SS, 110)
    d = ImageDraw.Draw(img)
    r_dot = 16 * SS
    d.ellipse([px - r_dot, py - r_dot, px + r_dot, py + r_dot], fill=(255, 122, 61))
    finalize(img, "logo_v2_C.png")


design_a()
design_b()
design_c()
print("ALL DONE")
