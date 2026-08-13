# -*- coding: utf-8 -*-
"""分析QQ全窗口截图底部区域，定位输入框边界（找水平边框线）"""
from PIL import Image

img = Image.open(r'D:\7tan\7tanAI\qq_full_now.png')  # 1080x640（窗口460,200起）
W, H = img.size
print('size:', W, H)
px = img.load()

# 聊天区底部区域：图内 x 280-900（对应屏幕740-1360），y 550-640（对应750-840）
def row_stats(y, x0=280, x1=900):
    grays = 0
    whites = 0
    darks = 0
    total = x1 - x0
    for x in range(x0, x1):
        r, g, b = px[x, y][:3]
        if abs(r-g) < 15 and abs(g-b) < 15:
            if r > 200:
                whites += 1
            elif r < 120:
                darks += 1
            else:
                grays += 1
    return whites, grays, darks

print('y(rel) -> 屏幕y -> whites/grays/darks')
for y in range(545, 640):
    w, g, d = row_stats(y)
    flag = ''
    if g > 200 or d > 400:
        flag = ' <<< BORDER?'
    print(f'{y} -> {y+200}: w={w} g={g} d={d}{flag}')
