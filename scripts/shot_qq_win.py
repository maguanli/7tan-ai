# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
from mss.tools import to_png

# 窗口位置 (480,200) 1060x640
left, top, w, h = 480, 200, 1060, 640
with mss.mss() as sct:
    region = {'left': left, 'top': top, 'width': w, 'height': h}
    shot = sct.grab(region)
    to_png(shot.rgb, shot.size, output=r'data\screenshots\qq_window.png')
    print('已保存 data/screenshots/qq_window.png')

    # 左侧列表区域（假设群列表在左侧约 300px 宽）
    region_left = {'left': left, 'top': top, 'width': 320, 'height': h}
    shot2 = sct.grab(region_left)
    to_png(shot2.rgb, shot2.size, output=r'data\screenshots\qq_left.png')
    print('已保存 data/screenshots/qq_left.png')
