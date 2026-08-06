# -*- coding: utf-8 -*-
"""放大识别浏览器地址栏 URL"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
from PIL import Image

async def recognize(pil_img):
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    data = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    if hasattr(writer, "store"):
        writer.store()
    else:
        await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = ocr.OcrEngine.try_create_from_language(glob.Language("zh-CN"))
    result = await engine.recognize_async(bitmap)
    items = []
    for line in result.lines:
        for word in line.words:
            r = word.bounding_rect
            items.append((word.text, r.x, r.y, r.width, r.height))
    return items

async def main():
    img = Image.open(r"D:\7tan\7tanAI\data\screenshots\_current_screen.png")
    # 地址栏区域放大
    crop = img.crop((330, 132, 900, 170))
    crop = crop.resize((crop.width*3, crop.height*3), Image.LANCZOS)
    crop.save(r"D:\7tan\7tanAI\data\screenshots\_url_bar.png")
    items = await recognize(crop)
    items.sort(key=lambda it: it[1])
    print("地址栏内容:")
    for t, x, y, w, h in items:
        print(f"  {t!r}")

asyncio.run(main())
