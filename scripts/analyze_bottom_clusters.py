# -*- coding: utf-8 -*-
"""分析窗口底部深色元素聚类，定位发送按钮/工具栏/输入框"""
from PIL import Image
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

img = Image.open(r'D:\7tan\7tanAI\scripts\qq_bottom_area.png').convert('RGB')
arr = np.array(img).astype(int)
h, w, _ = arr.shape
# 深色像素（非白非浅灰）
dark = (arr.sum(axis=2) < 500)
print(f'底部区域 {w}x{h}，深色像素: {dark.sum()} ({dark.mean()*100:.2f}%)')

# 按 y 分段统计深色
print('\n=== 深色像素 y 分布（每10px，绝对坐标 y=440+） ===')
for y in range(0, h, 10):
    cnt = dark[y:y+10, :].sum()
    if cnt > 100:
        print(f'  abs_y={440+y:4d}: {cnt}')

# 聚类：找深色像素的连通区域（简化：按 x 范围聚类每 20px 行带）
print('\n=== 深色元素位置（y带 + x范围） ===')
for y in range(0, h, 20):
    row_dark = dark[y:y+20, :]
    cnt = row_dark.sum()
    if cnt > 50:
        cols = np.where(row_dark.any(axis=0))[0]
        if len(cols):
            print(f'  abs_y={440+y:4d}-{440+y+20}: x={cols.min()+480}-{cols.max()+480} cnt={cnt}')
