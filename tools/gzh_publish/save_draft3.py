# -*- coding: utf-8 -*-
"""再点保存草稿(760,931)→全屏OCR确认状态"""
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
    pyautogui.click(760, 931)
    time.sleep(3.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/full_after_save3.png')
    words = asyncio.run(ocr_words('data/screenshots/full_after_save3.png'))
    for text, x, y, w, h in words:
        t = text.strip()
        if t in ('保', '存', '成', '功', '草', '稿', '已', '发', '表', '错', '误', '失', '败', '提', '示', '确', '定') or '保存' in t:
            print(f'{t!r} @ ({x},{y})')

if __name__ == '__main__':
    main()
