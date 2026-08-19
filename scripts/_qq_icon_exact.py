# -*- coding: utf-8 -*-
"""精确放大 QQ 图标块，定位图标中心坐标"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

from PIL import Image

async def recognize(pil_img):
    import io as _io
    buf = _io.BytesIO()
    pil_img.save(buf, format="PNG")
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(buf.getvalue())
    if hasattr(writer, "store"):
        writer.store()
    else:
        await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = ocr.OcrEngine.try_create_from_language(glob.Language("zh-CN"))
    result = await engine.recognize_async(bitmap)
    out = []
    for line in result.lines:
        for word in line.words:
            r = word.bounding_rect
            out.append((word.text, r.x, r.y, r.width, r.height))
    return out

async def main():
    img = Image.open(r"D:\7tan\7tanAI\data\screenshots\_desktop_now.png")
    # QQ 图标块: (0,568)-(120,700)，放大4倍精细识别
    box = (0, 560, 130, 700)
    crop = img.crop(box)
    big = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
    items = await recognize(big)
    print(f"=== QQ图标块识别 (原始区域 {box}) ===")
    for t, x, y, w, h in items:
        ox, oy = box[0] + x / 4, box[1] + y / 4
        print(f"  [{int(ox)},{int(oy)} {int(w/4)}x{int(h/4)}] {t!r}")

asyncio.run(main())
