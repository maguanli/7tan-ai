# -*- coding: utf-8 -*-
"""裁剪屏幕左上角侧边栏 logo 区域，放大4倍保存，供用户对比"""
from PIL import Image

im = Image.open(r"D:\7tan\7tanAI\_screen_now.png")
# 侧边栏 logo 区域（左侧顶部）裁剪稍大范围
crop = im.crop((0, 0, 260, 200)).convert("RGB")
big = crop.resize((260 * 4, 200 * 4), Image.NEAREST)
big.save(r"D:\7tan\7tanAI\_screen_crop_4x.png")
print("saved _screen_crop_4x.png", big.size)
