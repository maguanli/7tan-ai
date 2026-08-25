# -*- coding: utf-8 -*-
"""在 ch03_08.png 底部添加：偏差(红色) + 身在局外著(白色)"""
import os
from PIL import Image, ImageDraw, ImageFont

SRC = r"D:\用户目录\下载\新建文件夹 123\ch03_08.png"
OUT = r"D:\用户目录\下载\新建文件夹 123\ch03_08_封面.png"

FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"   # 微软雅黑粗体
FONT_REG  = r"C:\Windows\Fonts\msyh.ttc"     # 微软雅黑

def pick_font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    # fallback
    return ImageFont.load_default()

def main():
    if not os.path.exists(SRC):
        print("ERROR: 源图不存在:", SRC)
        return
    img = Image.open(SRC).convert("RGB")
    W, H = img.size
    print("源图尺寸:", W, H)

    # 底部渐变遮罩（增强可读性）
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    mask_h = int(H * 0.42)          # 底部 42% 区域做渐变
    y0 = H - mask_h
    for i in range(mask_h):
        alpha = int(140 * (i / mask_h) ** 1.5)   # 越往下越深
        od.line([(0, y0 + i), (W, y0 + i)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    # 文字布局（底部区域）
    title_font = pick_font([FONT_BOLD], int(H * 0.075))   # 大标题
    sub_font   = pick_font([FONT_REG],  int(H * 0.040))   # 小字

    title = "偏 差"
    sub   = "身在局外著"

    # 测量
    tb = d.textbbox((0, 0), title, font=title_font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    sb = d.textbbox((0, 0), sub, font=sub_font)
    sw, sh = sb[2] - sb[0], sb[3] - sb[1]

    # 位置：底部往上排
    margin_bottom = int(H * 0.045)
    sub_y = H - margin_bottom - sh
    gap = int(H * 0.015)
    title_y = sub_y - gap - th

    cx = W // 2
    # 标题：红色
    d.text((cx - tw / 2, title_y), title, font=title_font, fill=(255, 30, 30, 255),
           stroke_width=max(2, int(H * 0.004)), stroke_fill=(0, 0, 0))
    # 副标题：白色
    d.text((cx - sw / 2, sub_y), sub, font=sub_font, fill=(255, 255, 255, 255),
           stroke_width=max(1, int(H * 0.002)), stroke_fill=(0, 0, 0))

    img.save(OUT, quality=95)
    print("已保存:", OUT)
    print("标题位置 y:", title_y, " 副标题 y:", sub_y)

if __name__ == "__main__":
    main()
