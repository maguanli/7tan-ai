# -*- coding: utf-8 -*-
"""再试摘要框(750,625)，粘贴后OCR验证0/120变化"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pyperclip
import mss
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as gl
import winrt.windows.graphics.imaging as gimg
import winrt.windows.storage.streams as streams

DIGEST = '5亿人挤在同一个岛上是什么体验？陈星汉七年磨一剑有多治愈？3A级赛车在手机上是怎样的画质？这篇给你挖出5款不同类型、口碑爆棚的手机游戏，从爆笑派对到催泪治愈，从狂飙赛道到银河冒险，总有一款让你今晚睡不着。全程无广，放心食用。'

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
    pyperclip.copy(DIGEST)
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.5)
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 400, 'top': mon['top'] + 590, 'width': 560, 'height': 90}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/digest_v3.png')
    words = asyncio.run(ocr_words('data/screenshots/digest_v3.png'))
    for text, x, y, w, h in words:
        print(f'{text!r} @ screen({x+400},{y+590})')

if __name__ == '__main__':
    main()
