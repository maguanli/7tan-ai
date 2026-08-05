# -*- coding: utf-8 -*-
"""用 winsdk 调用 Windows 自带 OCR 识别截图文字"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path: str) -> str:
    file = await StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(0)          # FileAccessMode.Read
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        return "[无可用OCR引擎]"
    result = await engine.recognize_async(bitmap)
    lines = []
    for line in result.lines:
        lines.append(line.text)
    return "\n".join(lines)

if __name__ == "__main__":
    path = r"D:\7tan\7tanAI\wechat_screen.png"
    text = asyncio.run(ocr_file(path))
    print("=====OCR开始=====")
    print(text)
    print("=====OCR结束=====")
