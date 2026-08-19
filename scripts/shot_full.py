# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss

with mss.mss() as sct:
    mon = sct.monitors[1]  # 主显示器
    print('显示器:', mon)
    shot = sct.grab(mon)
    from mss.tools import to_png
    to_png(shot.rgb, shot.size, output=r'data\screenshots\qq_fullscreen.png')
    print('已保存 data/screenshots/qq_fullscreen.png')
