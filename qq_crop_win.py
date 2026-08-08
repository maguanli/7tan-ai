# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

im = Image.open("qq_activated.png").convert("RGB")
# QQ窗口区域 (795,285)-(1125,755)，裁剪并放大1.5倍
crop = im.crop((790, 280, 1130, 760))
crop = crop.resize((int(crop.width * 1.5), int(crop.height * 1.5)), Image.LANCZOS)
crop.save("qq_crop.png")
print("qq_crop.png saved, size:", crop.size)
