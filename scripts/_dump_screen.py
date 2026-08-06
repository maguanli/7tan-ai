# -*- coding: utf-8 -*-
"""全屏 OCR 输出全部文字+坐标，判断当前页面状态"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

import mss, io as _io
from PIL import Image

async def recognize_with_positions(pil_img):
    buf = _io.BytesIO()
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
    img.save(r"D:\7tan\7tanAI\data\screenshots\_current_screen.png")
    print("截图:", img.size)
    items = await recognize_with_positions(img)
    print("识别词数:", len(items))
    # 按 y 排序输出
    items.sort(key=lambda it: (it[2], it[1]))
    for t, x, y, w, h in items:
        print(f"  [{int(x)},{int(y)} {int(w)}x{int(h)}] {t!r}")

asyncio.run(main())
