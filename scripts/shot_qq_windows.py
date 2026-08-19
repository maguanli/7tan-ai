# -*- coding: utf-8 -*-
"""截取两个QQ窗口区域保存图片，用于OCR识别群名"""
import mss
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

regions = {
    'qq_win_3672392': (560, 220, 800, 600),
    'qq_win_133662': (600, 200, 720, 640),
}

with mss.mss() as sct:
    for name, (x, y, w, h) in regions.items():
        monitor = {'left': x, 'top': y, 'width': w, 'height': h}
        img = sct.grab(monitor)
        out = rf'D:\7tan\7tanAI\scripts\{name}.png'
        mss.tools.to_png(img.rgb, img.size, output=out)
        print(f'{name} -> {out} ({w}x{h})')
