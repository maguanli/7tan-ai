# -*- coding: utf-8 -*-
"""裁剪弹层区域(视口)放大4倍OCR+颜色分析，找出所有可点击元素"""
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
    img = Image.open('data/screenshots/state_check.png').convert('RGB')
    # 弹层区域 x 150-420, y 200-400（视口）
    crop = img.crop((150, 200, 450, 400))
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    crop.save('data/screenshots/dialog_zoom3x.png')
    print('zoomed:', crop.size)
    words = asyncio.run(ocr_words('data/screenshots/dialog_zoom3x.png'))
    print('=====WORDS(offset 150,200, scale 3)=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({150+x//3},{200+y//3}) w={w//3} h={h//3}')
    print('=====COLORS=====')
    from collections import Counter
    counter = Counter()
    for yy in range(crop.height):
        for xx in range(crop.width):
            r, g, b = crop.getpixel((xx, yy))
            counter[(r//40*40, g//40*40, b//40*40)] += 1
    for color, cnt in counter.most_common(10):
        print(f'RGB~{color} count={cnt}')
    print('=====END=====')

if __name__ == '__main__':
    main()
