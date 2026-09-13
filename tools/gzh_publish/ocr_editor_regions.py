# -*- coding: utf-8 -*-
"""OCR编辑器区域下半部分(x180-900,y600-1080) 和 顶部按钮区(x180-900,y60-230)"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams

async def recognize(img_path):
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
    return result.text

def main():
    with mss.mss() as sct:
        mon = sct.monitors[1]
        r1 = {'left': mon['left'] + 180, 'top': mon['top'] + 600, 'width': 720, 'height': 480}
        img = sct.grab(r1)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/editor_lower.png')
        r2 = {'left': mon['left'] + 180, 'top': mon['top'] + 60, 'width': 720, 'height': 170}
        img2 = sct.grab(r2)
        img2 = Image.frombytes('RGB', img2.size, img2.rgb)
        img2.save('data/screenshots/editor_topbar.png')
    print('--- LOWER ---')
    print(asyncio.run(recognize('data/screenshots/editor_lower.png')))
    print('--- TOPBAR ---')
    print(asyncio.run(recognize('data/screenshots/editor_topbar.png')))

if __name__ == '__main__':
    main()
