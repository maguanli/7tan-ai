# -*- coding: utf-8 -*-
"""OCR wechat_now.png 看聊天区"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\wechat_now.png")
# 右侧聊天区
crop = img.crop((380, 60, 1460, 1040))
crop = crop.resize((int(crop.width*1.5), int(crop.height*1.5)), Image.LANCZOS)
crop.save(r"D:\7tan\7tanAI\data\screenshots\wechat_now_right.png")

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path: str, scale=1.5, ox=380, oy=60):
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

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_now_right.png"))
print("===== 右侧聊天区 (原图坐标) =====")
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
