# -*- coding: utf-8 -*-
"""验证太极图结构：检查关键点的颜色"""
from PIL import Image
import sys
sys.path.insert(0, r'D:\7tan\7tanAI\scripts')
from gen_taiji_icon import draw_taiji_icon

im = draw_taiji_icon(512, rounded=True).convert('RGBA')

def px(x, y):
    return im.getpixel((x, y))

cx = cy = 256
R = int(512 * 0.38)
r2 = R // 2
print('R=', R, 'r2=', r2)
checks = {
    '中心(应黑鱼/墨黑)': (cx, cy + r2 // 2),
    '顶部(白鱼头-米白)': (cx, cy - R + 20),
    '底部(黑鱼头-墨黑)': (cx, cy + R - 20),
    '左侧边缘(白鱼身-米白)': (cx - R + 20, cy),
    '右侧边缘(黑鱼身-墨黑)': (cx + R - 20, cy),
    '白鱼眼(上,应墨黑)': (cx, cy - r2),
    '黑鱼眼(下,应米白)': (cx, cy + r2),
    '右上(白鱼头延伸-米白)': (cx + r2, cy - r2),
    '左下(黑鱼头延伸-墨黑)': (cx - r2, cy + r2),
    '背景(深棕)': (30, 30),
}
for name, (x, y) in checks.items():
    print(f'{name}: {px(x, y)}')
