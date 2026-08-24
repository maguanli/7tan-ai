# -*- coding: utf-8 -*-
from PIL import Image
import os

path = r"D:\7tan\7tanAI\临时脚本\crh_original_new.jpg"
img = Image.open(path).convert("RGB")
w, h = img.size
print("size:", w, h)
print("file_size:", os.path.getsize(path))

# 区域平均色
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

# 生成 900px 副本
img2 = img.copy()
img2.thumbnail((900, 900))
out = r"D:\7tan\7tanAI\临时脚本\crh_900.jpg"
img2.save(out, "JPEG", quality=88)
print("saved:", out, os.path.getsize(out))
