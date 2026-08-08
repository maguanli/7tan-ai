# -*- coding: utf-8 -*-
"""分析输入框截图中的文字像素，验证粘贴是否成功"""
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

for name, path in [('输入框区域', r'D:\7tan\7tanAI\scripts\qq_input_zoom.png'),
                   ('输入框区域2', r'D:\7tan\7tanAI\scripts\qq_input_verify.png'),
                   ('整个窗口', r'D:\7tan\7tanAI\scripts\qq_win_full.png')]:
    img = Image.open(path).convert('L')
    w, h = img.size
    px = img.load()
    dark = 0
    total = w * h
    # 统计深色像素（<120）
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if px[x, y] < 120:
                dark += 1
    ratio = dark / (total / 4) * 100
    print(f"{name}: {w}x{h}, 深色像素比例 {ratio:.2f}%")
