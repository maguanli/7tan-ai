# -*- coding: utf-8 -*-
"""截取微信左侧联系人列表区域放大2倍，识别高亮选中的行"""
from PIL import ImageGrab, Image

bbox = (300, 130, 620, 860)
img = ImageGrab.grab(bbox=bbox)
w, h = img.size
img_big = img.resize((w * 2, h * 2), Image.LANCZOS)
out = r"D:\7tan\7tanAI\data\screenshots\list_highlight.png"
img_big.save(out)
print("SAVED:", out, "size:", img_big.size)
