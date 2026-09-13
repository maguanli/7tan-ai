# -*- coding: utf-8 -*-
"""设计 5 款 AI 风格侧边栏图标 + 对比预览图
输出: designs/sidebar_icons/
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

OUT = r"D:\7tan\7tanAI\designs\sidebar_icons"
os.makedirs(OUT, exist_ok=True)

# 品牌配色
CYAN = (0, 212, 255)
PURPLE = (124, 58, 237)
DEEP_BG = (15, 15, 35)          # #0f0f23 侧边栏
WHITE = (240, 244, 255)

def font(size, bold=True):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def v_gradient(size, c1, c2):
    """垂直渐变图 (c1 顶 -> c2 底)"""
    w, h = size
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    return img

def diag_gradient(size, c1, c2):
    """对角渐变 (左上 c1 -> 右下 c2)"""
    w, h = size
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    maxd = (w * w + h * h) ** 0.5
    for y in range(h):
        for x in range(w):
            t = (x + y) / maxd
            c = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            d.point((x, y), fill=c)
    return img

def glow_circle(draw, xy, r, color, layers=6):
    """光晕圆"""
    cx, cy = (xy[0] + xy[2]) / 2, (xy[1] + xy[3]) / 2
    for i in range(layers, 0, -1):
        rr = r * (1 + i * 0.16)
        alpha = int(60 / i)
        col = (color[0], color[1], color[2], alpha)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)

def supersample(size, draw_fn, scale=4):
    """4x 超采样抗锯齿"""
    big = draw_fn((size[0] * scale, size[1] * scale))
    return big.resize(size, Image.LANCZOS)

# ============ 方案 A：神经网络 (NetMind) ============
def icon_net(size=(256, 256)):
    def draw(sz):
        img = Image.new("RGBA", sz, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        W, H = sz
        cx, cy = W / 2, H / 2
        # 节点位置
        nodes = [(cx, cy - 78), (cx + 78, cy + 40), (cx - 78, cy + 40), (cx - 46, cy - 30), (cx + 46, cy - 30)]
        # 连线
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                d.line([a, b], fill=(0, 212, 255, 120), width=int(W * 0.012))
        # 光晕
        for n, c in zip(nodes, [PURPLE, CYAN, CYAN, PURPLE, CYAN]):
            glow_circle(d, (0, 0, 0, 0), 26, c)  # 占位无意义，下面重画
        # 重画: 中心大球(渐变) + 外圈小球
        r_big = W * 0.115
        grad = v_gradient((int(r_big * 2), int(r_big * 2)), CYAN, PURPLE).convert("RGBA")
        mask = Image.new("L", grad.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, grad.size[0] - 1, grad.size[1] - 1], fill=255)
        img.paste(grad, (int(cx - r_big), int(cy - r_big)), mask)
        # 中心高光
        hc = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(hc).ellipse([cx - r_big * 0.45, cy - r_big * 0.45, cx + r_big * 0.2, cy + r_big * 0.2],
                                   fill=(255, 255, 255, 90))
        img = Image.alpha_composite(img, hc)
        d = ImageDraw.Draw(img)
        for n, c in zip(nodes[1:], [CYAN, CYAN, PURPLE, PURPLE]):
            rr = W * 0.05
            d.ellipse([n[0] - rr, n[1] - rr, n[0] + rr, n[1] + rr], fill=c + (255,))
        return img
    return supersample((256, 256), draw)

# ============ 方案 B：芯片大脑 (ChipBrain) ============
def icon_chip(size=(256, 256)):
    def draw(sz):
        img = Image.new("RGBA", sz, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        W, H = sz
        cx, cy = W / 2, H / 2
        # 芯片主体（圆角方，深色底+青边框）
        x0, y0, x1, y1 = cx - 92, cy - 92, cx + 92, cy + 92
        r = 26
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(20, 26, 48, 255), outline=CYAN + (255,), width=int(W * 0.02))
        # 引脚
        pin_w = int(W * 0.07)
        for px in [cx - 70, cx - 20, cx + 30, cx + 70]:
            d.rounded_rectangle([px - pin_w / 2, y0 - 18, px + pin_w / 2, y0], 4, fill=CYAN + (255,))
            d.rounded_rectangle([px - pin_w / 2, y1, px + pin_w / 2, y1 + 18], 4, fill=CYAN + (255,))
        for py in [cy - 70, cy - 20, cy + 30, cy + 70]:
            d.rounded_rectangle([x0 - 18, py - pin_w / 2, x0, py + pin_w / 2], 4, fill=CYAN + (255,))
            d.rounded_rectangle([x1, py - pin_w / 2, x1 + 18, py + pin_w / 2], 4, fill=CYAN + (255,))
        # 内部大脑波形（紫）
        pts = []
        import math
        for i in range(0, 201):
            t = i / 200
            x = x0 + 24 + (x1 - x0 - 48) * t
            y = cy - 18 + math.sin(t * math.pi * 4) * 14 + math.sin(t * math.pi * 9) * 6
            pts.append((x, y))
        d.line(pts, fill=PURPLE + (255,), width=int(W * 0.02), joint="curve")
        # 中心圆点（青）
        d.ellipse([cx - 9, cy + 22, cx + 9, cy + 40], fill=CYAN + (255,))
        return img
    return supersample((256, 256), draw)

# ============ 方案 C：AI 徽章 ============
def icon_ai(size=(256, 256)):
    def draw(sz):
        img = Image.new("RGBA", sz, (0, 0, 0, 0))
        W, H = sz
        cx, cy = W / 2, H / 2
        # 圆角方块 + 对角渐变
        x0, y0, x1, y1 = cx - 96, cy - 96, cx + 96, cy + 96
        grad = diag_gradient((W, H), CYAN, PURPLE).convert("RGBA")
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=30, fill=255)
        img.paste(grad, (0, 0), mask)
        # 高光边
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0, y0, x1, y1], radius=30, outline=(255, 255, 255, 110), width=6)
        # AI 文字
        f = font(int(W * 0.36), bold=True)
        txt = "AI"
        bbox = d.textbbox((0, 0), txt, font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), txt, font=f, fill=WHITE + (255,))
        return img
    return supersample((256, 256), draw)

# ============ 方案 D：AI 机器人 ============
def icon_bot(size=(256, 256)):
    def draw(sz):
        img = Image.new("RGBA", sz, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        W, H = sz
        cx, cy = W / 2, H / 2
        # 天线
        d.line([cx, cy - 96, cx, cy - 118], fill=CYAN + (255,), width=int(W * 0.02))
        d.ellipse([cx - 9, cy - 132, cx + 9, cy - 114], fill=CYAN + (255,))
        # 头部（圆角方，深底青边）
        x0, y0, x1, y1 = cx - 84, cy - 92, cx + 84, cy + 84
        d.rounded_rectangle([x0, y0, x1, y1], radius=30, fill=(20, 26, 48, 255), outline=CYAN + (255,), width=int(W * 0.02))
        # 双眼（发光）
        glow_circle(d, (0, 0, 0, 0), 20, CYAN)
        d.ellipse([cx - 46, cy - 34, cx - 12, cy + 0], fill=CYAN + (255,))
        d.ellipse([cx + 12, cy - 34, cx + 46, cy + 0], fill=CYAN + (255,))
        # 瞳孔
        d.ellipse([cx - 40, cy - 28, cx - 18, cy - 6], fill=WHITE + (255,))
        d.ellipse([cx + 18, cy - 28, cx + 40, cy - 6], fill=WHITE + (255,))
        # 微笑
        d.arc([cx - 30, cy + 12, cx + 30, cy + 52], start=20, end=160, fill=PURPLE + (255,), width=int(W * 0.02))
        return img
    return supersample((256, 256), draw)

# ============ 方案 E：智能星火 ============
def icon_spark(size=(256, 256)):
    def draw(sz):
        img = Image.new("RGBA", sz, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        W, H = sz
        cx, cy = W / 2, H / 2
        # 大四角星（青，中心）
        def star(cx, cy, r_outer, r_inner, color, n=4, rot=-45):
            import math
            pts = []
            for i in range(n * 2):
                ang = math.radians(rot + i * 180 / n)
                r = r_outer if i % 2 == 0 else r_inner
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
            d.polygon(pts, fill=color + (255,))
        glow_circle(d, (0, 0, 0, 0), 40, CYAN)
        star(cx, cy - 6, 52, 22, CYAN)
        # 两颗小星（紫）
        star(cx - 62, cy + 66, 26, 11, PURPLE, rot=-20)
        star(cx + 64, cy + 58, 18, 8, PURPLE, rot=-60)
        # 底部弧线轨道（青）
        d.arc([cx - 88, cy + 44, cx + 88, cy + 132], start=15, end=165, fill=(0, 212, 255, 160), width=int(W * 0.015))
        return img
    return supersample((256, 256), draw)

# ============ 生成单款 + 对比预览图 ============
icons = {
    "A_神经网络": (icon_net(), "神经网络节点 · 智能互联"),
    "B_芯片大脑": (icon_chip(), "芯片 + 大脑波形 · AI 计算"),
    "C_AI徽章": (icon_ai(), "AI 字母徽章 · 简洁直白"),
    "D_机器人": (icon_bot(), "AI 机器人 · 智能助手"),
    "E_智能星火": (icon_spark(), "智能火花 · 创意灵感"),
}

for name, (img, _) in icons.items():
    fn = f"icon_{name.split('_')[0].lower()}.png"
    img.save(os.path.join(OUT, fn))
    print("saved", fn)

# 对比预览图：深色侧边栏背景，大图 + 实际大小效果
W, H = 1320, 420
preview = Image.new("RGB", (W, H), DEEP_BG)
d = ImageDraw.Draw(preview)
d.text((40, 26), "7Tan 侧边栏图标设计方案 (AI 风格)   —  请选择一款，或告诉我修改意见", font=font(30, True), fill=(226, 232, 240))
d.text((40, 74), "背景 = 实际侧边栏色 #0f0f23    大图 96px    小图 = 实际显示效果 36px (左侧栏 logo 尺寸)", font=font(18, False), fill=(148, 163, 184))

x = 40
for i, (name, (img, desc)) in enumerate(icons.items()):
    # 卡片底
    card_w = 232
    d.rounded_rectangle([x, 116, x + card_w, 392], radius=14, fill=(23, 30, 56), outline=(30, 41, 59))
    # 大图
    big = img.resize((96, 96), Image.LANCZOS)
    preview.paste(big, (x + (card_w - 96) // 2, 136), big)
    # 实际尺寸 36px（带光晕放大到 40 观察）
    small = img.resize((36, 36), Image.LANCZOS)
    preview.paste(small, (x + (card_w - 36) // 2, 262), small)
    d.text((x + 16, 322), name, font=font(22, True), fill=(0, 212, 255))
    d.text((x + 16, 356), desc, font=font(15, False), fill=(148, 163, 184))
    x += card_w + 18

preview.save(os.path.join(OUT, "icons_compare.png"))
print("saved icons_compare.png")
print("DONE ->", OUT)
