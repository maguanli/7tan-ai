# -*- coding: utf-8 -*-
"""撤销正文误粘贴+OCR设置栏找摘要框"""
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
    # 1. 撤销误粘贴
    pyautogui.hotkey('ctrl', 'z')
    time.sleep(1.0)
    print('undo done')
    # 2. OCR设置栏区域 (x380-900, y440-530) 找摘要框
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 380, 'top': mon['top'] + 440, 'width': 520, 'height': 90}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/digest_zone3.png')
    words = asyncio.run(ocr_words('data/screenshots/digest_zone3.png'))
    print('--- digest zone words ---')
    for text, x, y, w, h in words:
        print(f'{text!r} @ screen({x+380},{y+440})')

if __name__ == '__main__':
    main()
