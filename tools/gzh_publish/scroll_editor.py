# -*- coding: utf-8 -*-
"""滚动编辑器页面向下，OCR查看设置项（封面/摘要/原创）"""
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
    # 鼠标移到编辑器区域并向下滚动
    pyautogui.moveTo(500, 500)
    time.sleep(0.3)
    for _ in range(6):
        pyautogui.scroll(-800)
        time.sleep(0.4)
    time.sleep(1.0)
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 180, 'top': mon['top'] + 200, 'width': 720, 'height': 880}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/editor_scrolled.png')
        print('saved', img.size)
    text = asyncio.run(recognize('data/screenshots/editor_scrolled.png'))
    print('=====AFTER SCROLL=====')
    print(text)
    print('=====END=====')

if __name__ == '__main__':
    main()
