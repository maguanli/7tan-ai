# -*- coding: utf-8 -*-
"""OCR 识别 7723 群聊天窗口，找输入框"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import asyncio, io, tempfile, os
from PIL import Image

async def main():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile

    path = r"scripts\qq_7723_chat.png"
    img = Image.open(path).convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    fd, tmp = tempfile.mkstemp(suffix='.png')
    with os.fdopen(fd, 'wb') as f:
        f.write(buf.getvalue())
    sf = await StorageFile.get_file_from_path_async(tmp)
    stream = await sf.open_async(0)
    dec = await BitmapDecoder.create_async(stream)
    bitmap = await dec.get_software_bitmap_async()
    lang = Language('zh-Hans-CN')
    engine = OcrEngine.try_create_from_language(lang)
    result = await engine.recognize_async(bitmap)
    os.remove(tmp)

    for i, line in enumerate(result.lines):
        words = line.words
        xs, ys = [], []
        for w in words:
            try:
                r = w.bounding_rect
                xs.append(r.x); ys.append(r.y)
            except Exception:
                pass
        if xs:
            x = int(min(xs)); y = int(min(ys))
            rlist = [w.bounding_rect for w in words]
            x2 = int(max(r.x + r.width for r in rlist))
            y2 = int(max(r.y + r.height for r in rlist))
            print(f"({x:4d},{y:4d})-({x2:4d},{y2:4d}) {line.text}")
    print(f"TOTAL={len(result.lines)}")

asyncio.run(main())
