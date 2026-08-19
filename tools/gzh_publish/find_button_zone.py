# -*- coding: utf-8 -*-
"""分析弹窗底部按钮区域，输出非白像素行分布找按钮边界"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    src = 'data/screenshots/after_enter2.png'
    img = Image.open(src).convert('RGB')
    w, h = img.size
    # 逐行扫描 y 550-700, x 400-680
    print('---- 每行非白像素数(范围 x400-680) ----')
    for y in range(550, 700, 2):
        cnt = 0
        xs = []
        for x in range(400, 680):
            r, g, b = img.getpixel((x, y))
            if r < 240 or g < 240 or b < 240:
                cnt += 1
                if len(xs) < 5:
                    xs.append(x)
        if cnt > 3:
            print('y=%d cnt=%d first_x=%s' % (y, cnt, xs))
    # 找按钮区域色块：深色文字（灰度 <150）
    print('---- 深色像素块(灰度<150) ----')
    for y in range(560, 700, 2):
        cnt = 0
        xs = []
        for x in range(400, 680):
            r, g, b = img.getpixel((x, y))
            if (r + g + b) / 3 < 150:
                cnt += 1
                if len(xs) < 3:
                    xs.append(x)
        if cnt > 3:
            print('y=%d dark=%d xs=%s' % (y, cnt, xs))

if __name__ == '__main__':
    main()
