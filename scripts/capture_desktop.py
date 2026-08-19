# -*- coding: utf-8 -*-
"""用 mss 截取整个桌面屏幕"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import mss
from PIL import Image
import numpy as np

out = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/desktop_full.png'

with mss.mss() as sct:
    monitor = sct.monitors[1]  # 主屏
    print('monitor:', monitor)
    img = sct.grab(monitor)
    pil = Image.frombytes('RGB', img.size, img.rgb)
    pil.save(out)
    print('saved:', out, pil.size, os.path.getsize(out))
    arr = np.array(pil)
    print('mean RGB:', arr.mean(axis=(0, 1)).round(1))
    nonblack = (arr.sum(axis=2) > 30).mean()
    print('nonblack_ratio:', round(float(nonblack), 3))
