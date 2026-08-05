# -*- coding: utf-8 -*-
"""生成封面：7Tan AI工具更新已发布的软件信息（横图+竖图）"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT_DIR = r"D:\用户目录\下载\新建文件夹 123\11"
os.makedirs(OUT_DIR, exist_ok=True)
random.seed(42)

# ---------- 字体 ----------
def load_font(size):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()

# ---------- 基础工具 ----------
def lerp(a, b, t):
    return int(a + (b - a) * t)

def draw_bg(img):
    """深蓝->靛紫 垂直渐变"""
    W, H = img.size
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        if t < 0.55:
            tt = t / 0.55
            r, g, b = lerp(6, 46, tt), lerp(13, 30, tt), lerp(40, 92, tt)
        else:
            tt = (t - 0.55) / 0.45
            r, g, b = lerp(46, 12, tt), lerp(30, 14, tt), lerp(92, 46, tt)
        d.line([(0, y), (W, y)], fill=(r, g, b))

def add_glow(img, cx, cy, radius, rgb, alpha=120):
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    steps = 50
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        a = int(alpha * (1 - t) * (1 - t))
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*rgb, a))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.28))
    img.paste(layer, (0, 0), layer)

def add_grid(img, spacing=70, alpha=16):
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for x in range(0, W, spacing):
        ld.line([(x, 0), (x, H)], fill=(120, 180, 255, alpha))
    for y in range(0, H, spacing):
        ld.line([(0, y), (W, y)], fill=(120, 180, 255, alpha))
    img.paste(layer, (0, 0), layer)

def add_particles(img, count=110):
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for _ in range(count):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.choice([1, 1, 2])
        a = random.randint(60, 180)
        c = random.choice([(160, 210, 255), (190, 170, 255), (255, 255, 255)])
        ld.ellipse([x - r, y - r, x + r, y + r], fill=(*c, a))
    # 十字星光
    for _ in range(8):
        x, y = random.randint(int(W*0.1), int(W*0.9)), random.randint(int(H*0.1), int(H*0.9))
        L = random.randint(8, 16)
        ld.line([(x - L, y), (x + L, y)], fill=(255, 255, 255, 140), width=1)
        ld.line([(x, y - L), (x, y + L)], fill=(255, 255, 255, 140), width=1)
    img.paste(layer, (0, 0), layer)

def add_corners(img, length=56, thick=4, alpha=200):
    """四角科技角标"""
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    col = (120, 220, 255, alpha)
    m = 28
    # 左上
    ld.line([(m, m + length), (m, m), (m + length, m)], fill=col, width=thick)
    # 右上
    ld.line([(W - m - length, m), (W - m, m), (W - m, m + length)], fill=col, width=thick)
    # 左下
    ld.line([(m, H - m - length), (m, H - m), (m + length, H - m)], fill=col, width=thick)
    # 右下
    ld.line([(W - m - length, H - m), (W - m, H - m), (W - m, H - m - length)], fill=col, width=thick)
    img.paste(layer, (0, 0), layer)

def draw_badge(img, cx, cy, R):
    """7Tan 发光徽章"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 外环光晕
    for i in range(24, 0, -1):
        t = i / 24
        r = int(R * 1.28 * t)
        a = int(110 * (1 - t) ** 2)
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(80, 190, 255, a), width=3)
    # 渐变圆盘
    for i in range(20, 0, -1):
        t = i / 20
        r = int(R * t)
        rr = lerp(30, 16, t); gg = lerp(60, 22, t); bb = lerp(150, 78, t)
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(rr, gg, bb, 255))
    # 外圈描边
    ld.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(140, 220, 255, 255), width=5)
    ld.ellipse([cx - R + 9, cy - R + 9, cx + R - 9, cy + R - 9], outline=(90, 180, 240, 180), width=2)
    # 文字 7 / Tan
    f7 = load_font(int(R * 1.0))
    ft = load_font(int(R * 0.30))
    bbox7 = ld.textbbox((0, 0), "7", font=f7)
    w7 = bbox7[2] - bbox7[0]
    ld.text((cx - w7 / 2, cy - int(R * 0.62)), "7", font=f7, fill=(255, 255, 255, 255))
    bbox = ld.textbbox((0, 0), "Tan", font=ft)
    w = bbox[2] - bbox[0]
    ld.text((cx - w / 2, cy + int(R * 0.28)), "Tan", font=ft, fill=(120, 220, 255, 255))
    img.paste(layer, (0, 0), layer)

def glow_text(img, xy, text, font, fill, glow_rgb, radius=10, anchor="mm"):
    """发光文字: 先模糊叠加再画清晰"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text(xy, text, font=font, fill=(*glow_rgb, 200), anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(radius))
    img.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)

def draw_update_ring(img, cx, cy, R, color=(120, 220, 255)):
    """更新/同步 圆环箭头图标"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # 圆弧
    ld.arc([cx - R, cy - R, cx + R, cy + R], start=200, end=320, fill=(*color, 255), width=7)
    ld.arc([cx - R, cy - R, cx + R, cy + R], start=20, end=140, fill=(*color, 255), width=7)
    # 箭头1 (右上)
    import math as m
    a1 = m.radians(140)
    x1, y1 = cx + R * m.cos(a1), cy + R * m.sin(a1)
    ld.polygon([(x1, y1), (x1 - 26, y1 - 16), (x1 - 12, y1 - 34)], fill=(*color, 255))
    # 箭头2 (左下)
    a2 = m.radians(320)
    x2, y2 = cx + R * m.cos(a2), cy + R * m.sin(a2)
    ld.polygon([(x2, y2), (x2 + 26, y2 + 16), (x2 + 12, y2 + 34)], fill=(*color, 255))
    # 中心小圆
    ld.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(*color, 255))
    img.paste(layer, (0, 0), layer)

def draw_progress(img, cx, cy, width, height=22):
    """底部更新进度条"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x0 = cx - width // 2
    y0 = cy - height // 2
    ld.rounded_rectangle([x0, y0, x0 + width, y0 + height], radius=height // 2, outline=(120, 200, 255, 160), width=2)
    pw = int(width * 0.92)
    ld.rounded_rectangle([x0 + 3, y0 + 3, x0 + 3 + pw, y0 + height - 3], radius=(height - 6) // 2, fill=(70, 170, 255, 200))
    # 高光
    ld.rounded_rectangle([x0 + 3, y0 + 3, x0 + 3 + pw, y0 + height - 3], radius=(height - 6) // 2, fill=(180, 230, 255, 60))
    # 圆点
    dtx = x0 + 3 + pw
    ld.ellipse([dtx - height // 2, y0 + 2, dtx + height // 2, y0 + height - 2], fill=(255, 255, 255, 255))
    img.paste(layer, (0, 0), layer)

# ---------- 主绘制 ----------
def draw_cover(W, H, out_path):
    img = Image.new("RGB", (W, H), "#0b1026")
    draw_bg(img)
    # 光晕
    add_glow(img, int(W * 0.22), int(H * 0.28), int(min(W, H) * 0.55), (60, 110, 255), 100)
    add_glow(img, int(W * 0.82), int(H * 0.70), int(min(W, H) * 0.5), (150, 60, 255), 80)
    add_glow(img, int(W * 0.75), int(H * 0.18), int(min(W, H) * 0.35), (40, 220, 200), 70)
    add_grid(img)
    add_particles(img)
    add_corners(img)

    cx, cy = W // 2, H // 2

    # 更新圆环图标（主标题上方）
    icon_r = int(min(W, H) * 0.055)
    if W > H:  # 横图
        icon_cy = int(H * 0.30)
        title_y = int(H * 0.47)
        sub_y = int(H * 0.66)
        foot_y = int(H * 0.80)
        bar_y = int(H * 0.885)
        badge_y = int(H * 0.30)
        title_size = int(W * 0.058)
        sub_size = int(W * 0.032)
        foot_size = int(W * 0.019)
        badge_r = int(H * 0.095)
    else:  # 竖图
        icon_cy = int(H * 0.175)
        title_y = int(H * 0.315)
        sub_y = int(H * 0.46)
        foot_y = int(H * 0.545)
        bar_y = int(H * 0.615)
        badge_y = int(H * 0.76)
        title_size = int(W * 0.115)
        sub_size = int(W * 0.058)
        foot_size = int(W * 0.033)
        badge_r = int(W * 0.24)

    # 徽章（竖图放中间下方，横图放右上角）
    if W > H:
        draw_badge(img, int(W * 0.86), int(H * 0.16), badge_r)
    else:
        draw_badge(img, cx, badge_y, badge_r)

    # 更新图标 + 英文小字
    draw_update_ring(img, cx, icon_cy, icon_r)
    f_small = load_font(foot_size)
    d = ImageDraw.Draw(img)
    d.text((cx, icon_cy - icon_r - foot_size * 2.2), "UPDATE & SYNC", font=f_small, fill=(150, 210, 255, 255), anchor="mm")

    # 主标题
    f_title = load_font(title_size)
    glow_text(img, (cx, title_y), "7Tan AI 工具", f_title, (255, 255, 255), (80, 180, 255), radius=16)

    # 副标题
    f_sub = load_font(sub_size)
    glow_text(img, (cx, sub_y), "更新已发布的软件信息", f_sub, (170, 235, 255), (70, 160, 255), radius=8)

    # 底部说明
    d.text((cx, foot_y), "7Tan AI 智能发布引擎 · 一键同步更新", font=f_small, fill=(200, 225, 245, 255), anchor="mm")

    # 进度条
    bar_w = int(W * 0.5) if W > H else int(W * 0.66)
    draw_progress(img, cx, bar_y, bar_w)
    d.text((cx, bar_y + 34), "已更新软件信息 · 100%", font=f_small, fill=(140, 200, 255, 255), anchor="mm")

    img.save(out_path, "PNG")
    print(f"[OK] {out_path}  {os.path.getsize(out_path)//1024} KB")

# ---------- 生成 ----------
draw_cover(1920, 1080, os.path.join(OUT_DIR, "7TanAI工具更新已发布的软件信息_横图_1920x1080.png"))
draw_cover(1080, 1920, os.path.join(OUT_DIR, "7TanAI工具更新已发布的软件信息_竖图_1080x1920.png"))
print("ALL DONE")
