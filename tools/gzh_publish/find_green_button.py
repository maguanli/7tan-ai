# -*- coding: utf-8 -*-
"""在底部工具栏区域找绿色按钮色块（微信绿 #07C160）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    img = Image.open('data/screenshots/full_bottom.png').convert('RGB')
    w, h = img.size
    # 底部工具栏区域 x 750-1300, y 880-1000
    x0, y0, x1, y1 = 750, 880, 1300, 1000
    green = []
    for y in range(y0, min(y1, h)):
        for x in range(x0, min(x1, w)):
            r, g, b = img.getpixel((x, y))
            # 微信绿 #07C160: r~7 g~193 b~96；宽松匹配
            if g > 120 and g > r * 2.2 and g > b * 1.5 and b > r:
                green.append((x, y, r, g, b))
    print('green pixels:', len(green))
    if green:
        xs = [p[0] for p in green]
        ys = [p[1] for p in green]
        print('green bbox: x[%d..%d] y[%d..%d]' % (min(xs), max(xs), min(ys), max(ys)))
        # 聚类：按 y 分段
        rows = {}
        for x, y, r, g, b in green:
            rows.setdefault(y // 10, []).append((x, y))
        for ky in sorted(rows):
            pts = rows[ky]
            xs2 = [p[0] for p in pts]
            print('yband %d: n=%d x[%d..%d]' % (ky * 10, len(pts), min(xs2), max(xs2)))
    # 也找蓝色按钮
    blue = []
    for y in range(y0, min(y1, h)):
        for x in range(x0, min(x1, w)):
            r, g, b = img.getpixel((x, y))
            if b > 120 and b - r > 60 and b - g > 40:
                blue.append((x, y))
    print('blue pixels:', len(blue))
    if blue:
        xs = [p[0] for p in blue]
        ys = [p[1] for p in blue]
        print('blue bbox: x[%d..%d] y[%d..%d]' % (min(xs), max(xs), min(ys), max(ys)))

if __name__ == '__main__':
    main()
