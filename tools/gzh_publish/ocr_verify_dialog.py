# -*- coding: utf-8 -*-
"""OCR微信验证弹窗区域 (240,250)-(1250,850)"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageOps, ImageEnhance
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
    img = Image.open('data/screenshots/after_final_confirm.png').convert('RGB')
    crop = img.crop((240, 250, 1250, 850))
    g = ImageOps.grayscale(crop)
    inv = ImageOps.invert(g)
    inv = ImageEnhance.Contrast(inv).enhance(2.0)
    inv = inv.resize((int(inv.width * 2), int(inv.height * 2)), Image.LANCZOS)
    inv.save('data/screenshots/verify_dialog.png')
    words = asyncio.run(ocr_words('data/screenshots/verify_dialog.png'))
    print('=====WORDS(offset 240,250, scale 2)=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({240+x//2},{250+y//2}) w={w//2} h={h//2}')
    print('=====END=====')

if __name__ == '__main__':
    main()
