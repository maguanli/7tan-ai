# -*- coding: utf-8 -*-
"""全屏OCR单字搜索：草稿/封面/摘要/原创/赞赏/发表/预览"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams

CHARS = ['草', '稿', '封', '面', '摘', '要', '原', '创', '赞', '赏', '发', '表', '预', '览', '声', '明', '未', '已', '拖', '拽', '合', '集', '链', '接']

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
        img.save('data/screenshots/full_scan2.png')
    words = asyncio.run(ocr_words('data/screenshots/full_scan2.png'))
    seen = set()
    for text, x, y, w, h in words:
        for ch in CHARS:
            if ch in text:
                key = (ch, x//20, y//20)
                if key not in seen:
                    seen.add(key)
                    print(f'「{ch}」 {text!r} @ ({x},{y})')
                break

if __name__ == '__main__':
    main()
