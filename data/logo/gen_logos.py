# -*- coding: utf-8 -*-
"""本地免费绘制公众号 LOGO 候选（PIL 超采样抗锯齿，零成本）"""
import os, math
from PIL import Image, ImageDraw

OUT = r"D:\7tan\7tanAI\data\logo"
os.makedirs(OUT, exist_ok=True)
SS = 4  # 超采样倍数，抗锯齿

def finish(img, base):
    img = img.resize((800, 800), Image.LANCZOS)
    img.save(os.path.join(OUT, base + ".png"))
    img.resize((360, 360), Image.LANCZOS).save(os.path.join(OUT, base + "_360.png"))
    print("saved:", base)

def canvas(bg="white"):
    img = Image.new("RGB", (800 * SS, 800 * SS), bg)
    return ImageDraw.Draw(img), img

def pt(x, y):
    return (x * SS, y * SS)

# ---------- 方案A：白底·深蓝人生曲线·橙色登顶小人 ----------
d, img = canvas("white")
pts = []
for i in range(200):
    t = i / 199.0
    x = 80 + t * 640
    y = 640 - 160 * math.sin(t * math.pi * 2.2) - 330 * t
    pts.append((x, y))
d.line([pt(x, y) for x, y in pts], fill=(28, 48, 88), width=int(26 * SS), joint="curve")
# 起点圆点
d.ellipse([pt(60, 648), pt(108, 696)], fill=(255, 140, 40))
# 终点登顶小人
cx, cy = 710, 310
d.ellipse([pt(cx - 22, cy - 96), pt(cx + 22, cy - 52)], fill=(255, 140, 40))   # 头
d.line([pt(cx, cy - 52), pt(cx, cy + 10)], fill=(255, 140, 40), width=int(16 * SS))  # 身体
d.line([pt(cx, cy - 30), pt(cx - 42, cy - 66)], fill=(255, 140, 40), width=int(12 * SS))  # 左臂
d.line([pt(cx, cy - 30), pt(cx + 42, cy - 66)], fill=(255, 140, 40), width=int(12 * SS))  # 右臂
d.line([pt(cx, cy + 10), pt(cx - 26, cy + 56)], fill=(255, 140, 40), width=int(12 * SS))   # 左腿
d.line([pt(cx, cy + 10), pt(cx + 26, cy + 56)], fill=(255, 140, 40), width=int(12 * SS))   # 右腿
finish(img, "logo_A_wave")

# ---------- 方案B：白底·双山登顶·红旗 ----------
d, img = canvas("white")
# 矮山（低谷）
d.polygon([pt(60, 700), pt(240, 700), pt(360, 430), pt(480, 700)], fill=(210, 212, 218))
# 高山（巅峰）
d.polygon([pt(300, 700), pt(560, 700), pt(720, 150), pt(780, 700)], fill=(58, 62, 74))
# 起点小圆
d.ellipse([pt(120, 640), pt(168, 688)], fill=(255, 140, 40))
# 红旗
d.line([pt(720, 150), pt(720, 40)], fill=(40, 40, 46), width=int(12 * SS))
d.polygon([pt(720, 40), pt(792, 66), pt(720, 92)], fill=(220, 50, 50))
finish(img, "logo_B_mountain")

# ---------- 方案C：深蓝圆底·金色波浪·白色小人 ----------
d, img = canvas("white")
d.ellipse([pt(0, 0), pt(800, 800)], fill=(22, 40, 82))
# 金色波浪（从谷底到高峰）
pts = []
for i in range(200):
    t = i / 199.0
    x = 130 + t * 540
    y = 560 - 120 * math.sin(t * math.pi * 2.2) - 260 * t
    pts.append((x, y))
d.line([pt(x, y) for x, y in pts], fill=(245, 190, 60), width=int(24 * SS), joint="curve")
# 谷底金星
cx0, cy0 = 100, 560
d.ellipse([pt(cx0 - 30, cy0 - 30), pt(cx0 + 30, cy0 + 30)], fill=(245, 190, 60))
# 山顶白色小人（张开双臂）
cx, cy = 670, 300
d.ellipse([pt(cx - 22, cy - 96), pt(cx + 22, cy - 52)], fill=(255, 255, 255))
d.line([pt(cx, cy - 52), pt(cx, cy + 10)], fill=(255, 255, 255), width=int(16 * SS))
d.line([pt(cx, cy - 30), pt(cx - 42, cy - 66)], fill=(255, 255, 255), width=int(12 * SS))
d.line([pt(cx, cy - 30), pt(cx + 42, cy - 66)], fill=(255, 255, 255), width=int(12 * SS))
d.line([pt(cx, cy + 10), pt(cx - 26, cy + 56)], fill=(255, 255, 255), width=int(12 * SS))
d.line([pt(cx, cy + 10), pt(cx + 26, cy + 56)], fill=(255, 255, 255), width=int(12 * SS))
finish(img, "logo_C_circle")

print("ALL DONE ->", OUT)
