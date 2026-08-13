# -*- coding: utf-8 -*-
"""读取屏幕指定区域文字（winsdk OCR，更准）"""
import asyncio, io, sys
import mss
from PIL import Image
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

REGION = sys.argv[1] if len(sys.argv) > 1 else None  # x,y,w,h

async def ocr_region(img, region=None):
    if region:
        x, y, w, h = [int(v) for v in region.split(',')]
        img = img.crop((x, y, x+w, y+h))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    result = await engine.recognize_async(bitmap)
    return [(line.text, None) for line in result.lines]

def main():
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    lines = asyncio.run(ocr_region(img, REGION))
    for text, rect in lines:
        print(text)

if __name__ == "__main__":
    main()
