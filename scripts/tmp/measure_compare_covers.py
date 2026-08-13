# -*- coding: utf-8 -*-
"""对比第二章与第四章封面的文字块测量结果"""
from PIL import Image

def measure(path, label):
    img = Image.open(path).convert('RGB')
    W, H = img.size
    px = img.load()
    yellow_rows = []
    white_rows = []
    for y in range(H):
        yc = 0
        wc = 0
        for x in range(0, W, 2):
            r, g, b = px[x, y]
            if r > 200 and g > 170 and b < 130:
                yc += 1
            elif r > 235 and g > 235 and b > 235:
                wc += 1
        if yc > 3:
            yellow_rows.append((y, yc))
        if wc > 5:
            white_rows.append((y, wc))

    def cluster(rows, gap=12):
        groups = []
        cur = []
        prev = -100
        for y, c in rows:
            if y - prev > gap and cur:
                groups.append(cur)
                cur = []
            cur.append((y, c))
            prev = y
        if cur:
            groups.append(cur)
        out = []
        for g in groups:
            ys = [y for y, c in g]
            cs = [c for y, c in g]
            out.append((min(ys), max(ys), sum(cs)))
        return out

    def hspan(y0, y1, color):
        xs = []
        for y in range(y0, y1 + 1):
            for x in range(0, W):
                r, g, b = px[x, y]
                if color == 'yellow' and r > 200 and g > 170 and b < 130:
                    xs.append(x)
                elif color == 'white' and r > 235 and g > 235 and b > 235:
                    xs.append(x)
        if not xs:
            return None
        return min(xs), max(xs)

    print(f'===== {label} ({W}x{H}) =====')
    for tag, groups, color in [('黄', cluster(yellow_rows), 'yellow'), ('白', cluster(white_rows), 'white')]:
        for (y0, y1, c) in groups:
            hs = hspan(y0, y1, color)
            if hs:
                print(f'  {tag}文字块: y={y0}~{y1} (高{y1-y0+1}), x={hs[0]}~{hs[1]} (宽{hs[1]-hs[0]+1}), 中心x={(hs[0]+hs[1])//2}, 中心y={(y0+y1)//2}')

measure(r'D:\用户目录\下载\新建文件夹 123\cover_ch2_vertical.png', '第二章封面')
measure(r'D:\用户目录\下载\新建文件夹 123\cover_ch4_vertical.png', '第四章封面')
