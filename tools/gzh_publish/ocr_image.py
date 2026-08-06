# -*- coding: utf-8 -*-
"""OCR指定图片，输出全部词+坐标"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams

async def ocr_words(img_path):
    engine = ocr.OcrEngine.try_create_from_language(gl.Language('zh-Hans-CN'))
    with open(img_path, 'rb') as f:
        data = f.read()
    stream = streams.InMemoryRandomAccessStream()
    writer = streams.DataWriter(stream)
    writer.write_bytes(data)
    writer.store_async().get()
    stream.seek(0)
    decoder = await gimg.BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    result = await engine.recognize_async(bitmap)
    out = []
    for line in result.lines:
        for w in line.words:
            r = w.bounding_rect
            out.append((w.text, int(r.x), int(r.y), int(r.width), int(r.height)))
    return out

def main():
    img_path = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/publish_dialog.png'
    words = asyncio.run(ocr_words(img_path))
    print('=====WORDS=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({x},{y}) w={w} h={h}')
    print('=====END=====')

if __name__ == '__main__':
    main()
