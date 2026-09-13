# -*- coding: utf-8 -*-
"""裁剪全屏截图指定区域并OCR"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image
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
    src = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/full_publish.png'
    x0, y0, x1, y1 = [int(v) for v in (sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])]
    img = Image.open(src)
    crop = img.crop((x0, y0, x1, y1))
    crop.save('data/screenshots/crop_zone2.png')
    print('crop:', crop.size)
    words = asyncio.run(ocr_words('data/screenshots/crop_zone2.png'))
    print('=====WORDS(offset %d,%d)=====' % (x0, y0))
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({x+x0},{y+y0}) w={w} h={h}')
    print('=====END=====')

if __name__ == '__main__':
    main()
