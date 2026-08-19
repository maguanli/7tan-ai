# -*- coding: utf-8 -*-
"""截图微信聊天窗口标题栏区域并放大，便于视觉识别"""
from PIL import ImageGrab, Image
import sys

# 微信窗口区域：标题栏在右侧聊天区顶部
bbox = (600, 100, 1250, 240)
img = ImageGrab.grab(bbox=bbox)
# 放大3倍
w, h = img.size
img_big = img.resize((w * 3, h * 3), Image.LANCZOS)
out = r"D:\7tan\7tanAI\data\screenshots\title_bar_3x.png"
img_big.save(out)
print("SAVED:", out, "size:", img_big.size)
