# -*- coding: utf-8 -*-
"""裁剪图片下半部分并OCR（找弹窗按钮）"""
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
    src = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/publish_dialog2.png'
    y0 = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    y1 = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    img = Image.open(src)
    w, h = img.size
    crop = img.crop((0, y0, w, y1))
    crop.save('data/screenshots/crop_zone.png')
    print('crop zone:', crop.size, 'orig:', img.size)
    words = asyncio.run(ocr_words('data/screenshots/crop_zone.png'))
    print('=====WORDS(y offset +%d)=====' % y0)
    for text, x, y, w2, h2 in words:
        print(f'{text!r} @ ({x},{y+y0}) w={w2} h={h2}')
    print('=====END=====')

if __name__ == '__main__':
    main()
