# -*- coding: utf-8 -*-
"""全屏OCR搜索关键按钮：封面/摘要/原创/赞赏/保存为草稿/发表"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams

KEYWORDS = ['封面', '摘要', '原创', '赞赏', '留言', '合集', '原文', '创作', '广告', '推荐', '草稿', '发表', '预览', '声明', '未声明', '已开启', '拖拽']

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
        img.save('data/screenshots/full_scan.png')
    words = asyncio.run(ocr_words('data/screenshots/full_scan.png'))
    # 按关键词过滤（单个字也匹配）
    for text, x, y, w, h in words:
        for kw in KEYWORDS:
            if kw in text:
                print(f'[{kw}] {text!r} @ ({x},{y})')
                break

if __name__ == '__main__':
    main()
