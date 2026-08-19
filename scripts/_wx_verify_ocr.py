# -*- coding: utf-8 -*-
"""验证微信发送结果：OCR 检查发送后截图（asyncio 风格）"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import winsdk.windows.media.ocr as ocr
    import winsdk.windows.globalization as glob
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
except ImportError:
    from winrt.windows.media.ocr import OcrEngine as ocr
    import winrt.windows.globalization as glob
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

from PIL import Image

lang = glob.Language("zh-CN")
engine = ocr.OcrEngine.try_create_from_language(lang)
if engine is None:
    engine = ocr.OcrEngine.try_create_from_user_profile_languages()

async def recognize(pil_img):
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(buf.getvalue())
    await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    result = await engine.recognize_async(bitmap)
    return result.text

async def main():
    img = Image.open(r'D:\7tan\7tanAI\data\screenshots\wx_fast_after.png')
    text = await recognize(img)
    print("===== OCR 全文 =====")
    print(text)
    print("===== 关键词检查 =====")
    for kw in ['7坛游戏社区', '红火', '推荐', '游戏']:
        print(f"  {kw}: {'✅ 找到' if kw in text else '❌ 未找到'}")

asyncio.run(main())
