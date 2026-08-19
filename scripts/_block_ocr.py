# -*- coding: utf-8 -*-
"""分块 OCR 浏览器区域，判断页面类型"""
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
    # 浏览器区域分块识别
    blocks = [
        ("顶部", 295, 125, 1095, 440),
        ("中部", 295, 440, 1095, 710),
        ("下部", 295, 710, 1095, 1060),
    ]
    for name, x1, y1, x2, y2 in blocks:
        crop = img.crop((x1, y1, x2, y2))
        crop = crop.resize((int(crop.width*1.5), int(crop.height*1.5)), Image.LANCZOS)
        items = await recognize(crop)
        items.sort(key=lambda it: (round(it[2]/10), it[1]))
        print(f"\n===== {name} ({x1},{y1})-({x2},{y2}) 词数{len(items)} =====")
        line_text = {}
        for t, x, y, w, h in items:
            ox, oy = int(x1 + x/1.5), int(y1 + y/1.5)
            key = oy
            line_text.setdefault(key, []).append((ox, t))
        for oy in sorted(line_text):
            parts = sorted(line_text[oy])
            s = " ".join(t for _, t in parts)
            print(f"  y={oy}: {s}")

asyncio.run(main())
