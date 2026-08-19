# -*- coding: utf-8 -*-
"""点击(750,625)后typewrite('abc')，OCR验证0/120变化"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
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
    pyautogui.click(750, 625)
    time.sleep(0.8)
    pyautogui.typewrite('abc', interval=0.1)
    time.sleep(1.0)
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 400, 'top': mon['top'] + 590, 'width': 560, 'height': 90}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/digest_abc.png')
    words = asyncio.run(ocr_words('data/screenshots/digest_abc.png'))
    for text, x, y, w, h in words:
        print(f'{text!r} @ screen({x+400},{y+590})')

if __name__ == '__main__':
    main()
