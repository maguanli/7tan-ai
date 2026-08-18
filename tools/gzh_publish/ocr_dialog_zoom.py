# -*- coding: utf-8 -*-
"""裁剪+放大2倍+OCR，提高弹窗识别率"""
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
    src = 'data/screenshots/full_publish.png'
    img = Image.open(src)
    crop = img.crop((380, 420, 700, 600))
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    crop.save('data/screenshots/dialog_zoom.png')
    print('zoomed:', crop.size)
    words = asyncio.run(ocr_words('data/screenshots/dialog_zoom.png'))
    print('=====WORDS(offset 380,420, scale 2)=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({380+x//2},{420+y//2}) w={w//2} h={h//2}')
    print('=====END=====')

if __name__ == '__main__':
    main()
