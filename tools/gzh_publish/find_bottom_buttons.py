# -*- coding: utf-8 -*-
"""裁剪底部工具栏区域放大OCR，定位发表按钮"""
import sys, io, asyncio, time, ctypes
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
    user32 = ctypes.windll.user32
    user32.ShowWindow(132302, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(132302)
    time.sleep(1.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/full_bottom.png')
    # 底部工具栏区域 x 650-1250, y 850-1020
    img2 = Image.open('data/screenshots/full_bottom.png')
    crop = img2.crop((650, 850, 1300, 1030))
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    crop.save('data/screenshots/bottom_zoom.png')
    words = asyncio.run(ocr_words('data/screenshots/bottom_zoom.png'))
    print('=====WORDS(offset 650,850, scale 2)=====')
    for text, x, y, w, h in words:
        print(f'{text!r} @ ({650+x//2},{850+y//2}) w={w//2} h={h//2}')
    print('=====END=====')

if __name__ == '__main__':
    main()
