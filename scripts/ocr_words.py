# -*- coding: utf-8 -*-
"""逐词 OCR 输出所有文字及位置"""
import sys, asyncio, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
from PIL import Image

def grab_region(x, y, w, h):
    with mss.mss() as sct:
        monitor = {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}
        shot = sct.grab(monitor)
    return Image.frombytes("RGB", shot.size, shot.rgb)

async def ocr_words_async(pil_img, offset_x=0, offset_y=0):
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
    result = await engine.recognize_async(bitmap)
    words = []
    for line in result.lines:
        for w in line.words:
            r = w.bounding_rect
            words.append((w.text, int(r.x + offset_x), int(r.y + offset_y), int(r.width), int(r.height)))
    return words

def main():
    args = sys.argv[1:]
    x, y, w, h = (int(v) for v in args[0].split(',')) if args else (600, 300, 766, 514)
    img = grab_region(x, y, w, h)
    words = asyncio.run(ocr_words_async(img, offset_x=x, offset_y=y))
    for text, lx, ly, lw, lh in sorted(words, key=lambda t: (t[2], t[1])):
        print(f'[{lx},{ly} {lw}x{lh}] {text}')
    print('===== END =====')

if __name__ == '__main__':
    main()
