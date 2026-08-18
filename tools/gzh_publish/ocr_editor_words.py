# -*- coding: utf-8 -*-
"""OCR编辑器区域，输出所有词+坐标，定位标题/作者/正文/摘要/原创/草稿按钮"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
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
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 180, 'top': mon['top'] + 120, 'width': 720, 'height': 700}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/editor_area_words.png')
    words = asyncio.run(ocr_words('data/screenshots/editor_area_words.png'))
    for text, x, y, w, h in words:
        # 转回屏幕坐标
        print(f'{text!r} @ screen({x+180},{y+120})')

if __name__ == '__main__':
    main()
