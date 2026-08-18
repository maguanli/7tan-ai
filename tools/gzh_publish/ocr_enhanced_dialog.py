# -*- coding: utf-8 -*-
"""图像增强OCR：灰度+反色+对比度，识别弹层隐藏元素"""
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
    img = Image.open('data/screenshots/full_latest.png').convert('RGB')
    crop = img.crop((380, 420, 700, 650))
    # 增强1：灰度+反色
    g = ImageOps.grayscale(crop)
    inv = ImageOps.invert(g)
    inv = ImageEnhance.Contrast(inv).enhance(2.0)
    inv = inv.resize((inv.width * 3, inv.height * 3), Image.LANCZOS)
    inv.save('data/screenshots/dialog_enhanced_inv.png')
    words = asyncio.run(ocr_words('data/screenshots/dialog_enhanced_inv.png'))
    print('=====WORDS(inverted, offset 380,420, scale 3)=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({380+x//3},{420+y//3})')
    # 增强2：原图放大
    crop2 = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    crop2.save('data/screenshots/dialog_enhanced_orig.png')
    words2 = asyncio.run(ocr_words('data/screenshots/dialog_enhanced_orig.png'))
    print('=====WORDS(original, offset 380,420, scale 3)=====')
    for text, x, y, w, h in words2:
        print(f'{text!r} @ ({380+x//3},{420+y//3})')
    print('=====END=====')

if __name__ == '__main__':
    main()
