# -*- coding: utf-8 -*-
"""修复 icon_d.png: 内容裁剪→放大居中→生成新 sidebar_icon.png + 对比预览"""
import os, shutil
from PIL import Image, ImageDraw

SRC = r'D:\7tan\7tanAI\designs\sidebar_icons\icon_d.png'
DST = r'D:\7tan\7tanAI\data\logo\sidebar_icon.png'
BAK = r'D:\7tan\7tanAI\designs\sidebar_icons\sidebar_icon_old_offcenter.bak.png'
PREVIEW = r'D:\7tan\7tanAI\designs\sidebar_icons\icon_d_fix_preview.png'

# 1. 读取原图
im = Image.open(SRC).convert('RGBA')
print('原图:', im.size)

# 2. 裁剪实际内容
alpha = im.split()[-1]
bbox = alpha.getbbox()
print('内容区域 bbox:', bbox)
content = im.crop(bbox)
print('内容尺寸:', content.size)

# 3. 内容等比缩放到 240x240 居中放入 256x256 画布
w, h = content.size
scale = 240 / max(w, h)
nw, nh = int(w * scale), int(h * scale)
content = content.resize((nw, nh), Image.LANCZOS)
canvas = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
canvas.paste(content, ((256 - nw) // 2, (256 - nh) // 2), content)
print('新画布图形 bbox:', canvas.split()[-1].getbbox())

# 4. 备份旧文件 + 写入新文件
if os.path.exists(DST):
    shutil.copy2(DST, BAK)
    print('已备份旧 sidebar_icon ->', BAK)
canvas.save(DST)
print('已写入新 sidebar_icon.png =', DST)

# 5. 生成对比预览：左侧=修复前28px效果(内容偏小) 右侧=修复后28px效果
prev = Image.new('RGBA', (420, 220), (15, 15, 35))
d = ImageDraw.Draw(prev)
d.text((12, 8), 'BEFORE (内容偏左上)', fill=(255, 100, 100))
d.text((232, 8), 'AFTER (居中放大)', fill=(100, 255, 100))
# before: 直接缩原图到28
before = im.resize((28, 28), Image.LANCZOS)
# after: 新图缩到28
after = canvas.resize((28, 28), Image.LANCZOS)
prev.paste(before, (20, 40), before)
prev.paste(after, (240, 40), after)
# 放大4x展示
prev = prev.resize((prev.width * 2, prev.height * 2), Image.NEAREST)
prev.save(PREVIEW)
print('对比预览已生成:', PREVIEW)
