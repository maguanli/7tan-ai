# -*- coding: utf-8 -*-
"""验证公众号编辑器表单填写状态：截图+裁剪+OCR（只识别上半屏，省CPU）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss, time
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams
import asyncio

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
        # 上半屏：高取 60%
        region = {'left': mon['left'], 'top': mon['top'], 'width': mon['width'], 'height': int(mon['height']*0.6)}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/editor_top_half.png')
        print('saved screenshot size:', img.size)
    text = asyncio.run(recognize('data/screenshots/editor_top_half.png'))
    print('=====OCR TOP HALF=====')
    print(text)
    print('=====END=====')

if __name__ == '__main__':
    main()
