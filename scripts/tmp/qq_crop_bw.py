# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageOps

im = Image.open("qq_activated.png").convert("RGB")
# 整个QQ窗口区域，放大2倍，并增强对比度
crop = im.crop((790, 280, 1130, 760))
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
# 灰度+对比度增强
g = ImageOps.autocontrast(crop.convert("L"))
g = g.point(lambda p: 255 if p > 140 else 0)
g.save("qq_crop_bw.png")
print("qq_crop_bw.png saved, size:", g.size)
