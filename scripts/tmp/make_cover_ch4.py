# -*- coding: utf-8 -*-
"""
第四章封面 - 严格复刻 cover_ch2_vertical.png 第二章封面样式
第二章封面实测参数(1080x1920):
  编号 00001  白色  字号~28  y中心~619(32%)  x中心~555
  角色名 黄毛  白色  字号~35  y中心~686(36%)  x中心~773
  章节标题    亮黄  字号~64  y中心~1606(84%) x中心~538
  书名       白色  字号~100 y中心~1734(90%) x中心~539
第四章: 编号00003 / 角色名陈默 / 第四章·系统剧本 / 《全球只有我是NPC》
底图: frames_ch4/frame_12.png
"""
from PIL import Image, ImageDraw, ImageFont

SRC = r'D:\7tan\7tanAI\downloads\fanqie\video\frames_ch4\frame_12.png'
OUT = r'D:\用户目录\下载\新建文件夹 123\cover_ch4_vertical.png'

W, H = 1080, 1920
im = Image.open(SRC).convert('RGB')

FONT_B = r'C:\Windows\Fonts\msyhbd.ttc'  # 微软雅黑粗体
FONT_R = r'C:\Windows\Fonts\msyh.ttc'    # 微软雅黑常规

def draw_text(draw, xy, text, font, fill, anchor='mm', shadow=True, shadow_offset=3):
    x, y = xy
    if shadow:
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 180), anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

draw = ImageDraw.Draw(im, 'RGBA')

# 1) 顶部 NPC候选编号 00003 (白色, 字号28, 参照第二章 y=32%, 水平居中偏右)
f_id = ImageFont.truetype(FONT_B, 28)
draw_text(draw, (555, int(H * 0.322)), '00003', f_id, (255, 255, 255, 255), shadow=True, shadow_offset=3)

# 2) 角色旁标注 陈默 (白色, 字号35, 参照第二章 y=36%, x=72%)
f_name = ImageFont.truetype(FONT_B, 35)
draw_text(draw, (int(W * 0.716), int(H * 0.357)), '陈默', f_name, (255, 255, 255, 255), shadow=True, shadow_offset=3)

# 3) 底部章节标题 第四章·系统剧本 (亮黄粗体, 字号64, y=84%)
f_ch = ImageFont.truetype(FONT_B, 64)
draw_text(draw, (W // 2, int(H * 0.836)), '第四章·系统剧本', f_ch, (255, 210, 40, 255), shadow=True, shadow_offset=4)

# 4) 最底部书名 《全球只有我是NPC》 (白色粗体, 字号100, y=90%)
f_title = ImageFont.truetype(FONT_B, 100)
draw_text(draw, (W // 2, int(H * 0.903)), '《全球只有我是NPC》', f_title, (255, 255, 255, 255), shadow=True, shadow_offset=4)

im.save(OUT)
print('saved:', OUT)
