# -*- coding: utf-8 -*-
"""预览太极图标效果"""
from PIL import Image
import sys
sys.path.insert(0, r'D:\7tan\7tanAI\scripts')
from gen_taiji_icon import draw_taiji_icon

canvas = Image.new('RGBA', (512, 512), (255, 255, 255, 255))
for i, (name, rounded) in enumerate([('方形', True), ('圆形', False)]):
    icon = draw_taiji_icon(256, rounded=rounded)
    canvas.paste(icon, (16 + i * 256, 128), icon)
canvas.save(r'D:\7tan\7tanAI\scripts\taiji_preview.png')
print('saved')
