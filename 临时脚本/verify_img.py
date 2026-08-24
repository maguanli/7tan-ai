# -*- coding: utf-8 -*-
import os
from PIL import Image

path = r"D:\用户目录\下载\新建文件夹 123\高铁换座\images\高铁换座_04_孩子看着.jpg"
img = Image.open(path)
print("format:", img.format)
print("size:", img.size)
print("mode:", img.mode)
print("file_size:", os.path.getsize(path), "bytes")
# 检查 EXIF
exif = img.getexif()
print("exif_keys:", list(exif.keys())[:10] if exif else "none")
# 缩略保存一份，用于视觉模型验证（避免缓存）
img.thumbnail((1200, 1200))
out = r"D:\7tan\7tanAI\临时脚本\img04_verify.jpg"
img.save(out, "JPEG", quality=90)
print("saved verify copy:", out, os.path.getsize(out))
