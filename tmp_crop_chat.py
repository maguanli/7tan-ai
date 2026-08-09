# -*- coding: utf-8 -*-
"""截取微信右侧聊天区域放大2倍，识别聊天内容"""
from PIL import ImageGrab, Image

bbox = (620, 200, 1269, 850)
img = ImageGrab.grab(bbox=bbox)
w, h = img.size
img_big = img.resize((w * 2, h * 2), Image.LANCZOS)
out = r"D:\7tan\7tanAI\data\screenshots\chat_content_2x.png"
img_big.save(out)
print("SAVED:", out, "size:", img_big.size)
