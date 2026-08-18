# -*- coding: utf-8 -*-
"""DOM聚焦摘要框后粘贴摘要，OCR验证"""
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

async def recognize(img_path):
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
    return result.text

def main():
    pyperclip.copy(DIGEST)
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.2)
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 300, 'top': mon['top'] + 400, 'width': 640, 'height': 200}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/digest_after2.png')
    text = asyncio.run(recognize('data/screenshots/digest_after2.png'))
    print('=====DIGEST ZONE 2=====')
    print(text)
    print('=====END=====')

if __name__ == '__main__':
    main()
