# -*- coding: utf-8 -*-
"""截图+裁剪右侧区域OCR，验证公众号编辑器填写状态"""
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
        W, H = mon['width'], mon['height']
        print('screen:', W, H)
        # 右侧 55% 区域（浏览器通常嵌在右侧）
        region = {'left': mon['left'] + int(W*0.40), 'top': mon['top'], 'width': int(W*0.60), 'height': H}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/editor_right.png')
        print('saved size:', img.size)
    text = asyncio.run(recognize('data/screenshots/editor_right.png'))
    print('=====OCR RIGHT 60%=====')
    print(text)
    print('=====END=====')

if __name__ == '__main__':
    main()
