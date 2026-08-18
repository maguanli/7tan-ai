# -*- coding: utf-8 -*-
"""全面分析弹层区域：找矩形色块(按钮边框)、图标、所有非文字元素"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image
from collections import Counter

def main():
    img = Image.open('data/screenshots/full_latest.png').convert('RGB')
    # 弹层完整区域 x 380-680, y 420-620
    x0, y0, x1, y1 = 380, 420, 680, 620
    # 找"边框色"像素：浅灰背景(224)之外的连续块
    # 先统计颜色
    counter = Counter()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = img.getpixel((x, y))
            counter[(r//16*16, g//16*16, b//16*16)] += 1
    print('===== 弹层完整区域主要颜色 =====')
    for color, cnt in counter.most_common(15):
        print(f'RGB~{color} count={cnt}')
    # 找非背景色块（背景=224,224,224 附近）
    print('===== 非背景色块分布(按10px网格) =====')
    grid = {}
    for y in range(y0, y1, 5):
        for x in range(x0, x1, 5):
            r, g, b = img.getpixel((x, y))
            if abs(r-224) > 40 or abs(g-224) > 40 or abs(b-224) > 40:
                key = (x//20*20, y//20*20)
                grid.setdefault(key, 0)
                grid[key] += 1
    for key in sorted(grid, key=lambda k: (k[1], k[0])):
        if grid[key] > 3:
            print(f'block @ ({key[0]},{key[1]}) hits={grid[key]}')

if __name__ == '__main__':
    main()
