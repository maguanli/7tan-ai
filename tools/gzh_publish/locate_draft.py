# -*- coding: utf-8 -*-
"""置前7Tan窗口 -> 全屏截图 -> OCR定位草稿标题/发表按钮坐标"""
import sys, io, asyncio, ctypes, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams

HWND = 132302  # 7Tan AI 窗口

def foreground(hwnd):
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.3)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)

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
    foreground(HWND)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/locate_draft.png')
        print('screen size:', img.size)
    words = asyncio.run(ocr_words('data/screenshots/locate_draft.png'))
    keys = ['5亿', '亿人', '治愈', '笑出', '发表', '草稿', '保存', '预览', '封面', '原创', '摘要', '手机游戏', '正在玩', '5款']
    print('=====KEYWORDS=====')
    for text, x, y, w, h in words:
        for k in keys:
            if k in text:
                print(f'{text!r} @ ({x},{y}) w={w} h={h}')
                break
    print('=====FIRST 40 WORDS=====')
    for text, x, y, w, h in words[:40]:
        print(f'{text!r} @ ({x},{y})')
    print('=====END=====')

if __name__ == '__main__':
    main()
