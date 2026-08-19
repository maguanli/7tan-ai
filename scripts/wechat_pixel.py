# -*- coding: utf-8 -*-
"""像素分析 wechat_now.png：判断右侧是空白还是OCR失效"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image
import collections

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\wechat_now.png").convert('RGB')
w, h = img.size
print('图片尺寸:', w, h)

# 分析三个区域的颜色分布
regions = {
    '左侧列表(60-380)': (60, 60, 380, 1040),
    '右侧聊天(400-1400)': (400, 100, 1400, 1000),
    '底部输入区(400-1400,900-1040)': (400, 900, 1400, 1040),
}
for name, (x0, y0, x1, y1) in regions.items():
    crop = img.crop((x0, y0, x1, y1))
    colors = crop.getcolors(maxcolors=100000)
    colors = sorted(colors, reverse=True)[:5]
    total = (x1-x0)*(y1-y0)
    top_pct = [(c, round(n/total*100, 1)) for n, c in colors]
    print(f'\n{name}: 主要颜色 {top_pct}')
    # 方差（内容复杂度）
    g = crop.convert('L')
    import statistics
    vals = list(g.getdata())
    mean = statistics.mean(vals)
    var = statistics.pstdev(vals)
    print(f'  灰度均值={mean:.1f} 标准差={var:.1f} (标准差大=内容多)')

# tesseract 检查
import shutil
print('\ntesseract:', shutil.which('tesseract'))
