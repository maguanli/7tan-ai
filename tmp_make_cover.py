# -*- coding: utf-8 -*-
"""基于 ch03_08.png 制作小说封面：底部加 偏差(红大字) + 身在局外著(白字)"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = r'D:\用户目录\下载\新建文件夹 123\ch03_08.png'
DST = r'D:\用户目录\下载\新建文件夹 123\ch03_08_封面.png'

img = Image.open(SRC).convert('RGB')
W, H = img.size  # 720 x 1203
draw = ImageDraw.Draw(img)

# ---------- 1. 底部渐变压暗（从 55% 高度到 100%，保证文字清晰） ----------
grad = Image.new('L', (1, H), 0)
for y in range(H):
    t = (y - int(H * 0.50)) / (H * 0.50)  # 50%处开始
    if t < 0:
        t = 0
    a = int(210 * t * t)  # 缓入
    grad.putpixel((0, y), a)
grad = grad.resize((W, H))
black = Image.new('RGB', (W, H), (0, 0, 0))
img = Image.composite(black, img, grad)
draw = ImageDraw.Draw(img)

# ---------- 2. 字体 ----------
font_title = ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc', 190)   # 偏差 超大
font_sub   = ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc', 96)    # 身在局外著

# ---------- 3. 文字（居中，底部） ----------
text1 = '偏差'
text2 = '身在局外著'

def text_bbox_center(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

w1, h1 = text_bbox_center(draw, text1, font_title)
w2, h2 = text_bbox_center(draw, text2, font_sub)

x1 = (W - w1) // 2
y1 = int(H * 0.72)          # 主标题 72% 高度（人物胸部区域，不遮脸）
x2 = (W - w2) // 2
y2 = y1 + h1 + 28           # 副标题紧跟其下

# 描边 + 填充（主标题红色、副标题白色）
draw.text((x1, y1), text1, font=font_title, fill=(225, 28, 28),
          stroke_width=8, stroke_fill=(10, 10, 10))
draw.text((x2, y2), text2, font=font_sub, fill=(255, 255, 255),
          stroke_width=4, stroke_fill=(10, 10, 10))

img.save(DST)
print('saved:', DST)
print('size:', img.size)
print('title y1-h1:', y1, y1 + h1, '| sub y2-h2:', y2, y2 + h2)
