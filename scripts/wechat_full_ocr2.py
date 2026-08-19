# -*- coding: utf-8 -*-
"""全屏OCR wechat_sent.png 看整体状态"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\wechat_sent.png")
img = img.resize((int(img.width*1.3), int(img.height*1.3)), Image.LANCZOS)
img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_sent_zoom.png")

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path: str, scale=1.3):
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
        out.append((int(x/scale), int(y/scale), wd, ht, line.text))
    return out

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_sent_zoom.png"))
print("===== 全屏内容 =====")
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
