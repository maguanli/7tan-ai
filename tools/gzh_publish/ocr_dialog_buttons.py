# -*- coding: utf-8 -*-
"""OCR弹层按钮区域 (650,670)-(1250,800)"""
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
    img = Image.open('data/screenshots/after_timing_click.png').convert('RGB')
    crop = img.crop((650, 670, 1250, 800))
    g = ImageOps.grayscale(crop)
    inv = ImageOps.invert(g)
    inv = ImageEnhance.Contrast(inv).enhance(2.0)
    inv = inv.resize((inv.width * 3, inv.height * 3), Image.LANCZOS)
    inv.save('data/screenshots/dialog_buttons.png')
    words = asyncio.run(ocr_words('data/screenshots/dialog_buttons.png'))
    print('=====WORDS(offset 650,670, scale 3)=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({650+x//3},{670+y//3})')
    # 颜色分析按钮区域
    from collections import Counter
    counter = Counter()
    for yy in range(0, crop.height):
        for xx in range(0, crop.width):
            r, g, b = crop.getpixel((xx, yy))
            counter[(r//32*32, g//32*32, b//32*32)] += 1
    print('=====COLORS=====')
    for color, cnt in counter.most_common(8):
        print(f'RGB~{color} count={cnt}')
    print('=====END=====')

if __name__ == '__main__':
    main()
