# -*- coding: utf-8 -*-
"""用 frame_01.png 合成小说封面 v3：书名分两行《全球只有我是 / NPC》+ 作者"""
from PIL import Image, ImageDraw, ImageFont
import os

SRC = r"D:\用户目录\下载\新建文件夹 123\frame_01.png"
OUT = r"D:\用户目录\下载\新建文件夹 123\cover_frame01.png"

FONT_TITLE = r"C:\Windows\Fonts\msyhbd.ttc"  # 微软雅黑粗体
FONT_AUTHOR = r"C:\Windows\Fonts\msyh.ttc"   # 微软雅黑

LINE1 = "全球只有我是"
LINE2 = "NPC"
AUTHOR = "身在局外 著"

def main():
    print("exists:", os.path.exists(SRC))
    im = Image.open(SRC).convert("RGB")
    W, H = im.size
    print("原图尺寸:", im.size)

    # 底部渐变加高到 36%，容纳两行书名 + 作者
    grad_h = int(H * 0.36)
    overlay = Image.new("RGBA", (W, grad_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(grad_h):
        alpha = int(210 * (y / grad_h) ** 1.3)
        d.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    im = im.convert("RGBA")
    im.paste(overlay, (0, H - grad_h), overlay)

    draw = ImageDraw.Draw(im)

    title_size = int(W * 0.13)      # 140px，保持大字
    title_font = ImageFont.truetype(FONT_TITLE, title_size)
    author_size = int(W * 0.058)
    author_font = ImageFont.truetype(FONT_AUTHOR, author_size)

    def draw_text_shadow(draw, xy, text, font, fill, offset=4):
        x, y = xy
        draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 220),
                  stroke_width=2, stroke_fill=(0, 0, 0, 200))
        draw.text((x, y), text, font=font, fill=fill,
                  stroke_width=2, stroke_fill=(0, 0, 0, 200))

    def center_x(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return (W - (bbox[2] - bbox[0])) // 2

    # 两行书名：行1「全球只有我是」，行2「NPC」，行距 title_size * 1.15
    line_gap = int(title_size * 1.15)
    start_y = H - grad_h + int(grad_h * 0.12)
    x1 = center_x(LINE1, title_font)
    draw_text_shadow(draw, (x1, start_y), LINE1, title_font, (255, 215, 0))
    x2 = center_x(LINE2, title_font)
    draw_text_shadow(draw, (x2, start_y + line_gap), LINE2, title_font, (255, 215, 0))

    # 作者名在两行书名下方
    ax = center_x(AUTHOR, author_font)
    ay = start_y + line_gap * 2 + int(grad_h * 0.08)
    draw_text_shadow(draw, (ax, ay), AUTHOR, author_font, (255, 255, 255))

    im = im.convert("RGB")
    im.save(OUT, quality=95)
    print("已保存:", OUT, im.size)

if __name__ == "__main__":
    main()
