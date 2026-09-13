# -*- coding: utf-8 -*-
"""全屏截图 -> OCR 指定区域(弹窗)找按钮"""
import sys, io, asyncio, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
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
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/full_publish.png')
        print('full size:', img.size)
    # 全屏弹窗区域 x 0-500 y 250-600
    img2 = Image.open('data/screenshots/full_publish.png')
    crop = img2.crop((0, 250, 600, 650))
    crop.save('data/screenshots/full_publish_zone.png')
    words = asyncio.run(ocr_words('data/screenshots/full_publish_zone.png'))
    print('=====WORDS(offset y+250)=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({x},{y+250}) w={w} h={h}')
    print('=====END=====')

if __name__ == '__main__':
    main()
