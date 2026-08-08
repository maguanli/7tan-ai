# -*- coding: utf-8 -*-
"""桌面图标网格切块 OCR：精确映射每个图标位置和名称"""
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
    W, H = img.size
    # 桌面图标：每列宽约 120px，每行高约 130px，从 (10, 50) 开始
    col_w, row_h = 120, 132
    start_x, start_y = 0, 40
    results = []
    for row in range(7):
        for col in range(6):
            x0 = start_x + col * col_w
            y0 = start_y + row * row_h
            x1, y1 = min(x0 + col_w, W), min(y0 + row_h, H)
            if y0 >= H or x0 >= W:
                continue
            crop = img.crop((x0, y0, x1, y1))
            big = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
            try:
                items = await recognize(big)
            except Exception as e:
                items = []
            texts = [t for t, *_ in items if t.strip()]
            joined = "".join(texts).replace(" ", "")
            if joined:
                results.append((x0, y0, joined))
    print("=== 桌面图标网格识别结果 ===")
    for x, y, txt in results:
        print(f"  网格起点({x},{y}) -> {txt!r}")

asyncio.run(main())
