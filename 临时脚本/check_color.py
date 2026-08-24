# -*- coding: utf-8 -*-
from PIL import Image
import os

path = r"D:\用户目录\下载\新建文件夹 123\高铁换座\images\高铁换座_04_孩子看着.jpg"
img = Image.open(path).convert("RGB")
w, h = img.size
print("size:", w, h)

# 分区域平均颜色
regions = {
    "top": (0, 0, w, h//4),
    "middle": (0, h//4, w, h*3//4),
    "bottom": (0, h*3//4, w, h),
}
for name, box in regions.items():
    crop = img.crop(box)
    px = list(crop.getdata())
    n = len(px)
    r = sum(p[0] for p in px) // n
    g = sum(p[1] for p in px) // n
    b = sum(p[2] for p in px) // n
    print(f"{name}: RGB({r},{g},{b})")

# 全图主色统计（降采样）
small = img.resize((100, 100))
colors = small.getcolors(10000)
colors.sort(reverse=True)
print("top colors:", [(c, rgb) for c, rgb in colors[:8]])
