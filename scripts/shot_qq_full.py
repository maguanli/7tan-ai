# -*- coding: utf-8 -*-
"""截取整个QQ窗口 + 输入框高分辨率区域，用于人工/OCR验证"""
import mss
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with mss.mss() as sct:
    # 整个窗口
    monitor = {'left': 600, 'top': 200, 'width': 720, 'height': 640}
    img = sct.grab(monitor)
    out1 = r'D:\7tan\7tanAI\scripts\qq_win_full.png'
    mss.tools.to_png(img.rgb, img.size, output=out1)
    print(f'整窗截图 -> {out1}')
    # 输入框候选区域放大：x 604-1220, y 660-790
    monitor2 = {'left': 604, 'top': 660, 'width': 616, 'height': 130}
    img2 = sct.grab(monitor2)
    out2 = r'D:\7tan\7tanAI\scripts\qq_input_zoom.png'
    mss.tools.to_png(img2.rgb, img2.size, output=out2)
    print(f'输入框放大 -> {out2}')
