# -*- coding: utf-8 -*-
"""截取微信窗口顶部区域并OCR，定位搜索框"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pygetwindow as gw

# 截取顶部区域
img = pyautogui.screenshot(region=(0, 0, 1000, 120))
img = img.resize((img.width * 2, img.height * 2))
img.save(r"D:\7tan\7tanAI\scan_top.png")
print("top saved", img.size)

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path: str):
    file = await StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    result = await engine.recognize_async(bitmap)
    out = []
    for line in result.lines:
        words = line.words
        if words:
            xs = [w.bounding_rect.x for w in words]
            ys = [w.bounding_rect.y for w in words]
            x2 = max(w.bounding_rect.x + w.bounding_rect.width for w in words)
            y2 = max(w.bounding_rect.y + w.bounding_rect.height for w in words)
            x, y = int(min(xs)), int(min(ys))
            wd, ht = int(x2 - x), int(y2 - y)
        else:
            x = y = wd = ht = 0
        out.append(f"[{x},{y} {wd}x{ht}] {line.text}")
    return "\n".join(out)

text = asyncio.run(ocr_file(r"D:\7tan\7tanAI\scan_top.png"))
print("=====TOP OCR=====")
print(text)
