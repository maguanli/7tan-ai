# -*- coding: utf-8 -*-
"""底部工具栏区域找所有非白大色块（按钮）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    img = Image.open('data/screenshots/full_bottom.png').convert('RGB')
    w, h = img.size
    x0, y0, x1, y1 = 750, 880, 1400, 1020
    # 每行统计非白像素段
    print('---- 非白像素按行 (x750-1400) ----')
    for y in range(y0, min(y1, h), 2):
        segments = []
        start = None
        for x in range(x0, min(x1, w)):
            r, g, b = img.getpixel((x, y))
            if (r + g + b) / 3 < 235:
                if start is None:
                    start = x
            else:
                if start is not None:
                    if x - start > 15:
                        segments.append((start, x))
                    start = None
        if start is not None and min(x1, w) - start > 15:
            segments.append((start, min(x1, w)))
        if segments:
            print('y=%d segs=%s' % (y, segments))
    # 深色像素（可能是深色按钮背景）
    print('---- 深色像素(灰度<100) x>900 ----')
    for y in range(y0, min(y1, h), 2):
        segs = []
        start = None
        for x in range(900, min(x1, w)):
            r, g, b = img.getpixel((x, y))
            if (r + g + b) / 3 < 100:
                if start is None:
                    start = x
            else:
                if start is not None:
                    if x - start > 10:
                        segs.append((start, x))
                    start = None
        if start is not None and min(x1, w) - start > 10:
            segs.append((start, min(x1, w)))
        if segs:
            print('y=%d dark_segs=%s' % (y, segs))

if __name__ == '__main__':
    main()
