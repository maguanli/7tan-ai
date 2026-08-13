# -*- coding: utf-8 -*-
"""截取微信左侧联系人列表区域并放大2倍，用于精确定位"""
from PIL import ImageGrab, Image

# 微信窗口: x=300,y=100,w=969,h=754。左侧联系人列表约 x=300-620, y=120-860
bbox = (300, 120, 620, 860)
img = ImageGrab.grab(bbox=bbox)
w, h = img.size
img_big = img.resize((w * 2, h * 2), Image.LANCZOS)
out = r"D:\7tan\7tanAI\data\screenshots\contact_list_2x.png"
img_big.save(out)
print("SAVED:", out, "size:", img_big.size, "orig:", img.size)
