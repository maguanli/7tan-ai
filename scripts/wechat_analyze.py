# -*- coding: utf-8 -*-
"""完整OCR wechat_chat2.png，分析左侧列表与右侧窗口"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\wechat_chat2.png")

# 左侧列表区域放大
left = img.crop((60, 60, 380, 1040))
left = left.resize((int(left.width*2), int(left.height*2)), Image.LANCZOS)
left.save(r"D:\7tan\7tanAI\data\screenshots\wechat_left.png")

# 右侧顶部 y 60-260
top = img.crop((380, 60, 1460, 260))
top = top.resize((int(top.width*2), int(top.height*2)), Image.LANCZOS)
top.save(r"D:\7tan\7tanAI\data\screenshots\wechat_top.png")

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path: str, scale=2, ox=0, oy=0):
    file = await StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    result = await engine.recognize_async(bitmap)
    out = []
    for line in result.lines:
        words = line.words
        if words:
            xs = [wd.bounding_rect.x for wd in words]
            ys = [wd.bounding_rect.y for wd in words]
            x2 = max(wd.bounding_rect.x + wd.bounding_rect.width for wd in words)
            y2 = max(wd.bounding_rect.y + wd.bounding_rect.height for wd in words)
            x, y = int(min(xs)), int(min(ys))
            wd, ht = int(x2 - x), int(y2 - y)
        else:
            x = y = wd = ht = 0
        out.append((int(x/scale+ox), int(y/scale+oy), wd, ht, line.text))
    return out

print("===== 左侧列表（放大2x, 原图坐标）=====")
for x, y, w, h, t in asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_left.png", 2, 60, 60)):
    print(f"[{x},{y} {w}x{h}] {t}")

print()
print("===== 右侧顶部标题区（放大2x, 原图坐标）=====")
for x, y, w, h, t in asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_top.png", 2, 380, 60)):
    print(f"[{x},{y} {w}x{h}] {t}")
