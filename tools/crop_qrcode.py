# -*- coding: utf-8 -*-
"""裁剪放大微信登录二维码"""
from PIL import Image

SRC = r'data/screenshots/微信登录二维码_重启后.png'
DST = r'data/screenshots/微信登录二维码_放大版.png'

img = Image.open(SRC)
w, h = img.size
print('原始尺寸:', w, h)

# 二维码通常在页面左中部（登录框区域），裁剪左侧 10%-45% 宽、15%-75% 高
crop = img.crop((int(w * 0.10), int(h * 0.15), int(w * 0.45), int(h * 0.75)))
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
crop.save(DST)
print('放大版已保存:', DST, crop.size)
