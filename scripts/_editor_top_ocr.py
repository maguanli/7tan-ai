# -*- coding: utf-8 -*-
"""截图 + OCR 编辑器顶部布局"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
from PIL import Image, ImageOps, ImageEnhance
import mss

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
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    img.save(r"D:\7tan\7tanAI\data\screenshots\_editor_top.png")
    # 顶部区域放大 OCR
    crop = img.crop((295, 125, 1095, 560))
    crop = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
    gray = ImageOps.grayscale(crop)
    gray = ImageEnhance.Contrast(gray).enhance(1.6)
    items = await recognize(gray)
    items.sort(key=lambda it: (round(it[2]/16), it[1]))
    lines = {}
    for t, x, y, w, h in items:
        oy = int(125 + y/2)
        ox = int(295 + x/2)
        key = oy // 6
        lines.setdefault(key, []).append((ox, t))
    print("=== 编辑器顶部布局 ===")
    for key in sorted(lines):
        parts = sorted(lines[key])
        oy = key * 6
        s = " ".join(t for _, t in parts)
        print(f"y={oy}: {s}")

asyncio.run(main())
