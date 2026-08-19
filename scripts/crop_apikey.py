# -*- coding: utf-8 -*-
from PIL import Image, ImageEnhance
img = Image.open(r'D:/用户目录/下载/新建文件夹 123/ScreenShot_2026-08-13_143728_404.png')
w, h = img.size
print('原图:', img.size)
# 裁剪表格区域（表格中部，API Key 列）：先裁出整行区域 y~150-280，x~550-1250
crop = img.crop((550, 140, 1250, 300))
crop = crop.resize((crop.width * 6, crop.height * 6), Image.LANCZOS)
crop = ImageEnhance.Contrast(crop).enhance(1.5)
crop.save(r'D:/7tan/7tanAI/data/logo/shot_apikey_crop.png')
print('裁剪放大保存:', crop.size)
