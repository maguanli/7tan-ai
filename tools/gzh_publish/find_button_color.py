# -*- coding: utf-8 -*-
"""分析弹窗区域颜色，定位绿色/蓝色按钮色块"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    src = 'data/screenshots/after_enter2.png'
    img = Image.open(src).convert('RGB')
    # 弹窗大致区域
    x0, y0, x1, y1 = 380, 420, 700, 640
    w, h = img.size
    # 找绿色系像素 (微信绿 #07C160) 和蓝色系
    green_pixels = []
    blue_pixels = []
    for y in range(y0, min(y1, h)):
        for x in range(x0, min(x1, w)):
            r, g, b = img.getpixel((x, y))
            # 绿色: g 明显大于 r 和 b
            if g > 100 and g - r > 40 and g - b > 40:
                green_pixels.append((x, y, r, g, b))
            # 蓝色
            elif b > 100 and b - r > 40 and b - g > 30:
                blue_pixels.append((x, y, r, g, b))
    print('green pixels:', len(green_pixels))
    if green_pixels:
        xs = [p[0] for p in green_pixels]
        ys = [p[1] for p in green_pixels]
        print('green bbox: x[%d..%d] y[%d..%d]' % (min(xs), max(xs), min(ys), max(ys)))
    print('blue pixels:', len(blue_pixels))
    if blue_pixels:
        xs = [p[0] for p in blue_pixels]
        ys = [p[1] for p in blue_pixels]
        print('blue bbox: x[%d..%d] y[%d..%d]' % (min(xs), max(xs), min(ys), max(ys)))
    # 也找弹窗背景(浅灰)范围，输出文字区域下方的非白像素分布
    print('---- 底部 y560-640 非白像素按x分布 ----')
    for y in range(560, 640, 4):
        cnt = 0
        for x in range(420, 660):
            r, g, b = img.getpixel((x, y))
            if r < 245 or g < 245 or b < 245:
                cnt += 1
        if cnt > 5:
            print('y=%d nonwhite=%d' % (y, cnt))

if __name__ == '__main__':
    main()
