# -*- coding: utf-8 -*-
"""local_ocr.py — 对本地图片做 OCR 验证文字内容"""
import asyncio
import io
import sys
from PIL import Image

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter


def ocr_file(path):
    img = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    async def _run():
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
        return result.text

    return asyncio.run(_run())


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            t = ocr_file(p).replace("\r", " ").replace("\n", " ")
            print(f"{p} => {t[:120]}")
        except Exception as e:
            print(f"{p} => ERROR {e}")
