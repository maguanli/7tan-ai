# -*- coding: utf-8 -*-
"""原版vs去水印版逐像素差分：精确定位所有被改动/残留的区域"""
import numpy as np
from PIL import Image
import subprocess, os

os.chdir(r'D:\7tan\7tanAI')

# 提取原版和干净版同一帧
for tag, f in [('orig', 'ch01_open_10s.mp4'), ('clean', 'ch01_open_10s_clean.mp4')]:
    subprocess.run(['ffmpeg', '-y', '-ss', '5', '-i', f'downloads/video_test/ch01/{f}',
                    '-frames:v', '1', f'downloads/video_test/ch01/diff_{tag}.png'],
                   capture_output=True)

a = np.array(Image.open('downloads/video_test/ch01/diff_orig.png').convert('RGB'), dtype=np.int16)
b = np.array(Image.open('downloads/video_test/ch01/diff_clean.png').convert('RGB'), dtype=np.int16)
d = np.abs(a - b).max(axis=2)  # 每像素最大通道差

# 全画面：找出所有差异区域
mask = d > 12  # 忽略微小编码噪声
ys, xs = np.where(mask)
print(f'全画面差异像素数: {len(xs)}')
if len(xs):
    print(f'差异范围: x[{xs.min()}~{xs.max()}] y[{ys.min()}~{ys.max()}]')
    # 聚类：按行段分组找独立区块
    from collections import defaultdict
    boxes = []
    used = np.zeros_like(mask)
    # 简易连通域：扫描差异像素的包围盒（分块统计）
    step = 60
    regions = defaultdict(int)
    for y, x in zip(ys, xs):
        regions[(y//step, x//step)] += 1
    hot = {k: v for k, v in regions.items() if v > 30}
    print('热点区块(60px网格, >30px):')
    for (gy, gx), cnt in sorted(hot.items()):
        print(f'  区域 x[{gx*60}~{gx*60+60}] y[{gy*60}~{gy*60+60}] 差异{cnt}px')

# 可视化差分热图
vis = np.zeros((1920, 1080, 3), dtype=np.uint8)
vis[..., 0] = np.clip(d * 8, 0, 255)
Image.fromarray(vis).save('downloads/video_test/ch01/diff_heat.png')
print('diff_heat.png saved')

# 干净版右下角再放大保存（人眼复核用）
im = Image.open('downloads/video_test/ch01/check_f5.png')
im.crop((700, 1760, 1080, 1920)).resize((1520, 640), Image.NEAREST).save(
    'downloads/video_test/ch01/corner_br_clean_big.png')
print('corner_br_clean_big.png saved')
