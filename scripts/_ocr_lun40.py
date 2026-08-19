# -*- coding: utf-8 -*-
"""OCR lun40 配图内容"""
import sys, io, asyncio, os
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
    return result.text

async def main():
    d = r"D:\7tan\7tanAI\data\screenshots\lun40"
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith(('.png', '.jpg')):
            continue
        p = os.path.join(d, f)
        img = Image.open(p)
        # 放大2x提升识别
        img2 = img.resize((img.width*2, img.height*2), Image.LANCZOS)
        text = await recognize(img2)
        print(f"\n===== {f} ({img.width}x{img.height}) =====")
        print(text.strip()[:400])

asyncio.run(main())
