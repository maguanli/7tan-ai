# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import os

src = r'D:\用户目录\下载\新建文件夹 123\ch03_08.png'
dst = r'D:\用户目录\下载\新建文件夹 123\ch03_08_封面.png'

im = Image.open(src).convert('RGB')
W, H = im.size
print('原图:', W, H)

# 底部渐变压暗遮罩
overlay = Image.new('RGBA', (W, H), (0,0,0,0))
od = ImageDraw.Draw(overlay)
for y in range(int(H*0.40), H):
    t = max(0.0, (y - H*0.40) / (H - H*0.40))
    a = int(190 * (t**1.5))
    od.line([(0,y),(W,y)], fill=(0,0,0,a))
im = Image.alpha_composite(im.convert('RGBA'), overlay).convert('RGB')

# 字体
font_path = None
for p in [r'C:\Windows\Fonts\msyhbd.ttc', r'C:\Windows\Fonts\msyh.ttc',
          r'C:\Windows\Fonts\simhei.ttf', r'C:\Windows\Fonts\simsun.ttc']:
    if os.path.exists(p):
        font_path = p
        break
print('字体:', font_path)

draw = ImageDraw.Draw(im)

def tb(text, font):
    return draw.textbbox((0,0), text, font=font)

# 主标题'只有我记得' 总宽约560
main_text = '只有我记得'
target_w = 560
size = 60
while size < 220:
    f = ImageFont.truetype(font_path, size)
    if draw.textlength(main_text, font=f) >= target_w:
        break
    size += 2
main_font = ImageFont.truetype(font_path, size)
main_w = draw.textlength(main_text, font=main_font)
mb = tb(main_text, main_font)
main_h = mb[3]-mb[1]

sub_text = '身在局外著'
sub_size = int(size*0.5)
sub_font = ImageFont.truetype(font_path, sub_size)
sub_w = draw.textlength(sub_text, font=sub_font)
sb = tb(sub_text, sub_font)
sub_h = sb[3]-sb[1]

gap = 48
cy_main = int(H*0.70)
y_main = cy_main - main_h//2
y_sub = y_main + main_h + gap

def stroke_text(x, y, text, font, fill, sw):
    draw.text((x, y), text, font=font, fill=fill,
              stroke_width=sw, stroke_fill=(0,0,0))

x_main = (W - main_w)//2
x_sub = (W - sub_w)//2
sw = max(4, size//14)
stroke_text(x_main, y_main, main_text, main_font, (225,30,30), sw)
stroke_text(x_sub, y_sub, sub_text, sub_font, (255,255,255), max(2, sub_size//16))

im.save(dst, quality=95)
print('已保存:', dst, os.path.getsize(dst), '字节')
print('主标题字号:', size, '宽:', int(main_w), '副标题字号:', sub_size)
print('主标题y:', y_main, '-', y_main+main_h, ' 副标题y:', y_sub, '-', y_sub+sub_h)
print('间距gap:', gap)
