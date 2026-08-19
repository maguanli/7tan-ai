# -*- coding: utf-8 -*-
"""截取QQ输入框区域验证粘贴结果"""
import mss
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with mss.mss() as sct:
    # 输入框区域: x 604~1220, y 640~800
    monitor = {'left': 604, 'top': 640, 'width': 616, 'height': 165}
    img = sct.grab(monitor)
    out = r'D:\7tan\7tanAI\scripts\qq_input_verify.png'
    mss.tools.to_png(img.rgb, img.size, output=out)
    print(f'输入框截图 -> {out}')
