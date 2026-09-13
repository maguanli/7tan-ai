# -*- coding: utf-8 -*-
"""OCR编辑器右侧设置栏 (x1080-1620, y250-720)"""
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
        region = {'left': mon['left'] + 1080, 'top': mon['top'] + 250, 'width': 540, 'height': 470}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/settings_panel.png')
        print('saved', img.size)
    text = asyncio.run(recognize('data/screenshots/settings_panel.png'))
    print('=====SETTINGS PANEL=====')
    print(text)
    print('=====END=====')

if __name__ == '__main__':
    main()
