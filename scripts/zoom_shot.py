# -*- coding: utf-8 -*-
from PIL import Image
img = Image.open(r'D:/用户目录/下载/新建文件夹 123/ScreenShot_2026-08-13_143728_404.png')
print('尺寸:', img.size)
w, h = img.size
img2 = img.resize((int(w * 2.5), int(h * 2.5)), Image.LANCZOS)
img2.save(r'D:/7tan/7tanAI/data/logo/shot_zoom.png')
print('已保存放大图:', img2.size)
