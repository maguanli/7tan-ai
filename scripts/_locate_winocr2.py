# -*- coding: utf-8 -*-
"""用 Windows OCR (winsdk) 识别全屏，返回带坐标的文字（asyncio 版）"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

import mss, io as _io
from PIL import Image

KEYWORD = "四十岁"

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
    print("截图:", img.size)

    small = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
    items = await recognize_with_positions(small)
    print("识别词数:", len(items))

    hits = []
    for t, x, y, w, h in items:
        if KEYWORD in t.replace(' ', ''):
            hits.append((t, int(x*2), int(y*2), int(w*2), int(h*2)))

    if hits:
        print("=== 命中「四十岁」 ===")
        for t, x, y, w, h in hits:
            print(f"text={t!r} x={x} y={y} w={w} h={h} 中心=({x+w//2},{y+h//2})")
    else:
        print("未命中关键词，输出部分文字(前50):")
        cnt = 0
        for t, x, y, w, h in items:
            print(f"  [{int(x*2)},{int(y*2)}] {t!r}")
            cnt += 1
            if cnt >= 50:
                break

asyncio.run(main())
