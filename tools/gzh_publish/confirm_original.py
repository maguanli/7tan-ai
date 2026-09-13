# -*- coding: utf-8 -*-
"""点击确定按钮(565,840)确认原创声明，OCR验证"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
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
    pyautogui.click(565, 840)
    time.sleep(2.0)
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 300, 'top': mon['top'] + 480, 'width': 640, 'height': 140}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/original_confirmed.png')
    text = asyncio.run(recognize('data/screenshots/original_confirmed.png'))
    print('=====ORIGINAL STATUS=====')
    print(text)
    print('=====END=====')

if __name__ == '__main__':
    main()
