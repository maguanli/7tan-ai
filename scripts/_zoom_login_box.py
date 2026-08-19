# -*- coding: utf-8 -*-
"""放大屏幕中央区域确认 QQ 登录窗口状态"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

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
    img = Image.open(r"D:\7tan\7tanAI\data\screenshots\_qq_state.png")
    # 中央区域
    box = (830, 480, 1080, 760)
    crop = img.crop(box)
    big = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    items = await recognize(big)
    print(f"=== 中央区域 OCR (原始 {box}) ===")
    items.sort(key=lambda it: (it[2], it[1]))
    for t, x, y, w, h in items:
        ox, oy = box[0] + x / 2, box[1] + y / 2
        print(f"  [{int(ox)},{int(oy)} {int(w/2)}x{int(h/2)}] {t!r}")

asyncio.run(main())
