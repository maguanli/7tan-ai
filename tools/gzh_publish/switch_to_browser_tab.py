# -*- coding: utf-8 -*-
"""截全屏→OCR找'浏览器'标签坐标→点击切换标签页"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams
import pyautogui, time

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
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/full_screen_tabs.png')
    words = asyncio.run(ocr_words('data/screenshots/full_screen_tabs.png'))
    targets = ['浏览器', '源码', '控制台', '对话']
    found = {}
    for text, x, y, w, h in words:
        t = text.strip()
        for tg in targets:
            if tg in t and tg not in found:
                found[tg] = (x + w//2, y + h//2, t)
    print('FOUND:', found)
    if '浏览器' in found:
        x, y, t = found['浏览器']
        print('clicking 浏览器 at', x, y)
        pyautogui.click(x, y)
        time.sleep(1.5)
        print('clicked')

if __name__ == '__main__':
    main()
