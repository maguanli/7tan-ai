# -*- coding: utf-8 -*-
"""分析弹窗区域颜色分布，找出按钮背景色块"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    src = 'data/screenshots/after_enter2.png'
    img = Image.open(src).convert('RGB')
    # 弹窗区域 x 420-620, y 430-560
    x0, y0, x1, y1 = 420, 430, 620, 560
    # 统计主要颜色
    from collections import Counter
    counter = Counter()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = img.getpixel((x, y))
            # 量化颜色
            counter[(r // 32 * 32, g // 32 * 32, b // 32 * 32)] += 1
    print('===== 弹窗区域主要颜色 =====')
    for color, cnt in counter.most_common(12):
        print(f'RGB~{color} count={cnt}')
    # 采样"发表"文字区域背景
    print('===== "发表"文字区域 (435,443)-(480,468) 像素 =====')
    sub = img.crop((435, 443, 480, 468))
    sub_counter = Counter()
    for y in range(sub.height):
        for x in range(sub.width):
            r, g, b = sub.getpixel((x, y))
            sub_counter[(r // 32 * 32, g // 32 * 32, b // 32 * 32)] += 1
    for color, cnt in sub_counter.most_common(6):
        print(f'RGB~{color} count={cnt}')
    # 弹窗边框找：扫描 y 420-580 每行的非白像素 x 范围（排除文字行）
    print('===== 弹窗垂直边框扫描 =====')
    for y in range(430, 580, 4):
        row_pixels = []
        for x in range(420, 620):
            r, g, b = img.getpixel((x, y))
            if (r + g + b) / 3 < 200:
                row_pixels.append(x)
        if row_pixels:
            print('y=%d dark_x=[%d..%d] n=%d' % (y, min(row_pixels), max(row_pixels), len(row_pixels)))

if __name__ == '__main__':
    main()
