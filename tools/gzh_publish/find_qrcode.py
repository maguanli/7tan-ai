# -*- coding: utf-8 -*-
"""定位并保存验证二维码图片"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    img = Image.open('data/screenshots/after_final_confirm.png').convert('RGB')
    # 找二维码：扫描 (240,320)-(1250,730) 区域的黑白密集块
    # 二维码特征：深色像素密集的方形区域
    from collections import Counter
    # 按 20px 网格统计深色像素
    x0, y0, x1, y1 = 240, 320, 1250, 730
    grid = {}
    for y in range(y0, y1, 4):
        for x in range(x0, x1, 4):
            r, g, b = img.getpixel((x, y))
            if (r + g + b) / 3 < 120:
                key = (x // 20 * 20, y // 20 * 20)
                grid[key] = grid.get(key, 0) + 1
    # 找密度最高的连续区域
    dense = {k: v for k, v in grid.items() if v > 12}  # 每个20x20块最多25个采样点
    if dense:
        xs = [k[0] for k in dense]
        ys = [k[1] for k in dense]
        print('dense bbox: x[%d..%d] y[%d..%d] count=%d' % (min(xs), max(xs), min(ys), max(ys), len(dense)))
        # 保存二维码区域（扩大padding）
        pad = 40
        crop = img.crop((max(0, min(xs) - pad), max(0, min(ys) - pad),
                         min(img.width, max(xs) + 20 + pad), min(img.height, max(ys) + 20 + pad)))
        crop.save('data/screenshots/verify_qrcode.png')
        print('saved verify_qrcode.png', crop.size)
    else:
        print('no dense block found')
        # 全区域深色像素分布
        print('total dark samples:', sum(grid.values()))

if __name__ == '__main__':
    main()
