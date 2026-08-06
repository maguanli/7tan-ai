# -*- coding: utf-8 -*-
"""裁剪浏览器区域并放大 OCR，细看《论四十岁》编辑页状态"""
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
    # 浏览器区域：左起 ~300 到 ~1090，上 ~130 到下 ~1060
    crop = img.crop((295, 125, 1095, 1060))
    # 放大1.5x提升识别
    crop = crop.resize((int(crop.width*1.5), int(crop.height*1.5)), Image.LANCZOS)
    crop.save(r"D:\7tan\7tanAI\data\screenshots\_browser_crop.png")
    items = await recognize(crop)
    items.sort(key=lambda it: (round(it[2]/10), it[1]))
    print("识别词数:", len(items))
    for t, x, y, w, h in items:
        # 坐标映射回原图
        ox, oy = int(295 + x/1.5), int(125 + y/1.5)
        print(f"  [{ox},{oy}] {t!r}")

asyncio.run(main())
