# -*- coding: utf-8 -*-
"""检查截图文件基本信息和颜色分布"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image
import numpy as np

p = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/wechat_check_1.png'
print('file:', p)
print('size_bytes:', os.path.getsize(p))
img = Image.open(p)
print('dims:', img.size, img.mode)
arr = np.array(img.convert('RGB'))
print('mean RGB:', arr.mean(axis=(0, 1)).round(1))
print('min/max:', int(arr.min()), int(arr.max()))
# 非黑像素比例
nonblack = (arr.sum(axis=2) > 30).mean()
print('nonblack_ratio:', round(float(nonblack), 3))
