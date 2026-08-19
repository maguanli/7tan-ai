# -*- coding: utf-8 -*-
"""
第三章封面 - 严格复刻第二章封面样式
底图: frames_ch3/frame_03.png (1080x1920)
样式参考 cover_ch2_vertical.png:
  顶部 00002 白色(荧光感) | 角色旁 秦朗 亮黄 | 底部 第三章·诚信NPC的代价 亮黄粗体 | 最底 《全球只有我是NPC》 白色粗体
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = r'D:\7tan\7tanAI\downloads\fanqie\video\frames_ch3\frame_03.png'
OUT = r'D:\用户目录\下载\新建文件夹 123\cover_ch3_vertical.png'

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

# 1) 顶部 NPC候选编号 00002 (白色荧光感, 约1/15宽=72px, 居中, 画面55%高度)
f_id = ImageFont.truetype(FONT_B, 72)
draw_text(draw, (W // 2, int(H * 0.545)), '00002', f_id, (255, 255, 255, 255), shadow=True, shadow_offset=4)

# 2) 角色旁标注 秦朗 (亮黄色, 约1/20宽=54px, 人物头顶偏右)
f_name = ImageFont.truetype(FONT_R, 54)
draw_text(draw, (int(W * 0.64), int(H * 0.415)), '秦朗', f_name, (255, 210, 40, 255), shadow=True, shadow_offset=3)

# 3) 底部章节标题 第三章·诚信NPC的代价 (亮黄粗体, 约1/10宽=108px, 82%高度)
f_ch = ImageFont.truetype(FONT_B, 108)
draw_text(draw, (W // 2, int(H * 0.82)), '第三章·诚信NPC的代价', f_ch, (255, 210, 40, 255), shadow=True, shadow_offset=5)

# 4) 最底部书名 《全球只有我是NPC》 (白色粗体, 约1/8宽=135px, 92%高度)
f_title = ImageFont.truetype(FONT_B, 135)
draw_text(draw, (W // 2, int(H * 0.92)), '《全球只有我是NPC》', f_title, (255, 255, 255, 255), shadow=True, shadow_offset=5)

im.save(OUT)
print('saved:', OUT)
