# -*- coding: utf-8 -*-
"""打印全屏OCR所有词+坐标，人工确认标签位置"""
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
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/full_screen_tabs.png')
    words = asyncio.run(ocr_words('data/screenshots/full_screen_tabs.png'))
    # 按y排序，只显示 y<400 的顶部词
    top = [w for w in words if w[2] < 400]
    top.sort(key=lambda w: (w[2], w[1]))
    for text, x, y, w, h in top:
        print(f'{text!r} @ ({x},{y}) {w}x{h}')

if __name__ == '__main__':
    main()
