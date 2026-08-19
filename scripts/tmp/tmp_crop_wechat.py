# -*- coding: utf-8 -*-
"""截取微信窗口区域（屏幕像素级，最可靠）"""
from PIL import ImageGrab, Image

# 微信窗口: x=300,y=100,w=969,h=754
bbox = (300, 100, 1269, 854)
img = ImageGrab.grab(bbox=bbox)
out = r"D:\7tan\7tanAI\data\screenshots\wechat_pil_now.png"
img.save(out)
print("SAVED:", out, "size:", img.size)
