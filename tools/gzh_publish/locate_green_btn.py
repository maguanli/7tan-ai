# -*- coding: utf-8 -*-
"""定位绿色按钮(确定/发表)像素位置"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    img = Image.open('data/screenshots/after_timing_click.png').convert('RGB')
    w, h = img.size
    green = []
    for y in range(600, 850):
        for x in range(400, 1300):
            r, g, b = img.getpixel((x, y))
            if g > 120 and g - r > 60 and g - b > 30 and b < 180:
                green.append((x, y, r, g, b))
    print('green pixels:', len(green))
    if green:
        xs = [p[0] for p in green]
        ys = [p[1] for p in green]
        print('green bbox: x[%d..%d] y[%d..%d]' % (min(xs), max(xs), min(ys), max(ys)))
        # 按y分段统计x范围（可能有多个绿色块）
        rows = {}
        for x, y, r, g, b in green:
            rows.setdefault(y // 5 * 5, []).append(x)
        for ky in sorted(rows):
            xs2 = rows[ky]
            print('yband %d: n=%d x[%d..%d]' % (ky, len(xs2), min(xs2), max(xs2)))
    # 找"取消"按钮框：文字(751,714) 周围
    print('--- 取消按钮区域颜色 (735,700)-(800,745) ---')
    from collections import Counter
    counter = Counter()
    for y in range(700, 745):
        for x in range(735, 800):
            r, g, b = img.getpixel((x, y))
            counter[(r//40*40, g//40*40, b//40*40)] += 1
    for color, cnt in counter.most_common(6):
        print(f'RGB~{color} count={cnt}')

if __name__ == '__main__':
    main()
