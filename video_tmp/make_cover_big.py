# -*- coding: utf-8 -*-
"""在 ch03_08.png 底部加大文字：偏差(红色) + 身在局外著(白色)"""
from PIL import Image, ImageDraw, ImageFont
import os

SRC = r"D:\用户目录\下载\新建文件夹 123\ch03_08.png"
DST = r"D:\用户目录\下载\新建文件夹 123\ch03_08_封面.png"

im = Image.open(SRC).convert("RGB")
W, H = im.size
print("原图尺寸:", im.size)

# 找系统中文字体
font_paths = [
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑粗体
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",   # 黑体
    r"C:\Windows\Fonts\simsun.ttc",   # 宋体
]
font_path = None
for fp in font_paths:
    if os.path.exists(fp):
        font_path = fp
        break
print("使用字体:", font_path)

# 加大字号：主标题 偏差 = 宽度的 13%，副标题 = 宽度的 6.5%
title_size = int(W * 0.13)
sub_size = int(W * 0.065)
print("主标题字号:", title_size, "副标题字号:", sub_size)

font_title = ImageFont.truetype(font_path, title_size)
font_sub = ImageFont.truetype(font_path, sub_size)

draw = ImageDraw.Draw(im)

# 文字内容
title_text = "偏差"
sub_text = "身在局外著"

# 用 getbbox 精确测量
def text_bbox_size(d, txt, fnt):
    bbox = d.textbbox((0, 0), txt, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

tw, th = text_bbox_size(draw, title_text, font_title)
sw, sh = text_bbox_size(draw, sub_text, font_sub)
print("主标题宽高:", tw, th, "副标题宽高:", sw, sh)

# 底部渐变暗角遮罩（从 62% 到 100% 渐暗，保证文字清晰）
overlay = Image.new("L", (W, H), 0)
od = ImageDraw.Draw(overlay)
start_y = int(H * 0.62)
for y in range(start_y, H):
    alpha = int(180 * (y - start_y) / (H - start_y))
    od.line([(0, y), (W, y)], fill=alpha)
im = Image.composite(im, Image.new("RGB", (W, H), (10, 10, 12)), overlay)
draw = ImageDraw.Draw(im)

# 主标题 "偏差" 居中，y = 80% 高度（更靠下且不遮脸）
title_y = int(H * 0.80) - th // 2
x = (W - tw) // 2
# 红色 + 黑色描边（描边加粗，字更醒目）
stroke = max(4, title_size // 16)
draw.text((x, title_y), title_text, font=font_title, fill=(220, 30, 30), stroke_width=stroke, stroke_fill=(0, 0, 0))

# 副标题 "身在局外著" 居中，主标题下方
sub_y = title_y + th + int(H * 0.02)
x2 = (W - sw) // 2
draw.text((x2, sub_y), sub_text, font=font_sub, fill=(255, 255, 255), stroke_width=max(2, sub_size // 16), stroke_fill=(0, 0, 0))

im.save(DST, "PNG")
print("已保存:", DST, im.size)
