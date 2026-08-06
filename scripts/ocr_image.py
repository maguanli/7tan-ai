# -*- coding: utf-8 -*-
"""OCR 图片文件"""
import sys, asyncio, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

async def ocr_async(pil_img):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    data = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        return "[OCR FAIL]"
    result = await engine.recognize_async(bitmap)
    return result.text

if __name__ == '__main__':
    path = sys.argv[1]
    img = Image.open(path)
    print(f"识别: {path} ({img.width}x{img.height})")
    text = asyncio.run(ocr_async(img))
    print("===== OCR 结果 =====")
    print(text)
    print("===== END =====")
