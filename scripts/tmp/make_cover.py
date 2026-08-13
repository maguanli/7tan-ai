# -*- coding: utf-8 -*-
"""用 frame_01.png 合成小说封面：底部加书名(两行) + 作者，字号大、位置上移"""
from PIL import Image, ImageDraw, ImageFont
import os

SRC = r"D:\用户目录\下载\新建文件夹 123\frame_01.png"
OUT = r"D:\用户目录\下载\新建文件夹 123\cover_frame01.png"

FONT_TITLE = r"C:\Windows\Fonts\msyhbd.ttc"  # 微软雅黑粗体
FONT_AUTHOR = r"C:\Windows\Fonts\msyh.ttc"   # 微软雅黑

TITLE_LINE1 = "全球只有我是"
TITLE_LINE2 = "NPC"
AUTHOR = "身在局外 著"

def draw_text_shadow(draw, cx, y, text, font, fill, stroke=6):
    """以 cx 为水平中心绘制带描边+投影的文字"""
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    tw = bbox[2] - bbox[0]
    x = cx - tw // 2 - bbox[0]
    # 投影
    draw.text((x + 6, y + 6), text, font=font, fill=(0, 0, 0, 230), stroke_width=stroke, stroke_fill=(0, 0, 0, 230))
    # 正文
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 230))
    return y + font.getbbox(text)[3] - font.getbbox(text)[1]

def main():
    print("exists:", os.path.exists(SRC))
    im = Image.open(SRC).convert("RGB")
    W, H = im.size
    print("原图尺寸:", im.size)

    # 底部渐变：加大到 36%，保证大字清晰可读
    grad_h = int(H * 0.36)
    overlay = Image.new("RGBA", (W, grad_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(grad_h):
        alpha = int(235 * (y / grad_h) ** 1.25)
        d.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    im = im.convert("RGBA")
    im.paste(overlay, (0, H - grad_h), overlay)

    draw = ImageDraw.Draw(im)

    # 字号：书名加大到画面宽 15%（约162px），作者 7%
    title_size = int(W * 0.15)
    author_size = int(W * 0.07)
    title_font = ImageFont.truetype(FONT_TITLE, title_size)
    author_font = ImageFont.truetype(FONT_AUTHOR, author_size)

    cx = W // 2
    # 书名再向上推移：起始位置定在画面约 53% 高度处（作者不动）
    y = int(H * 0.53)
    line_h = int(title_size * 1.12)

    y = draw_text_shadow(draw, cx, y, TITLE_LINE1, title_font, (255, 215, 0))
    y = draw_text_shadow(draw, cx, y + int(line_h * 0.10), TITLE_LINE2, title_font, (255, 215, 0))
    # 作者固定在原位（画面约 86% 高度处），不随书名上移
    author_y = int(H * 0.86)
    draw_text_shadow(draw, cx, author_y, AUTHOR, author_font, (255, 255, 255), stroke=5)

    im = im.convert("RGB")
    im.save(OUT, quality=95)
    print("已保存:", OUT, im.size, "| 书名起始y=", int(H * 0.53), "| 作者y=", int(H * 0.86))

if __name__ == "__main__":
    main()
