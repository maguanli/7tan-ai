# -*- coding: utf-8 -*-
"""放大指定区域精细 OCR，确认桌面 QQ 图标位置"""
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
    # 桌面图标第一列区域: 左上角 x=0-300, y=40-900，放大3倍
    regions = [
        ("左上全列", (0, 40, 320, 920)),
        ("第二列上部", (320, 40, 640, 500)),
    ]
    for name, box in regions:
        crop = img.crop(box)
        big = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
        items = await recognize(big)
        print(f"=== {name} 区域 (原始{box}) 放大3x ===")
        for t, x, y, w, h in items:
            # 坐标换算回原始图
            ox, oy = box[0] + x / 3, box[1] + y / 3
            print(f"  [{int(ox)},{int(oy)}] {t!r}")

asyncio.run(main())
