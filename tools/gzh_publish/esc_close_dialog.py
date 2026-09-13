# -*- coding: utf-8 -*-
"""按ESC关闭原创面板，OCR验证原创状态"""
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
    pyautogui.press('esc')
    time.sleep(1.5)
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 300, 'top': mon['top'] + 480, 'width': 640, 'height': 140}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/original_after_esc.png')
    text = asyncio.run(recognize('data/screenshots/original_after_esc.png'))
    print('=====AFTER ESC=====')
    print(text)
    print('=====END=====')

if __name__ == '__main__':
    main()
