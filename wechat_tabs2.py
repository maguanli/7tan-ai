# -*- coding: utf-8 -*-
"""放大OCR搜索面板 tab 行与排序行"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui

# tab 行区域 (1000,150)-(1936,240)
img = pyautogui.screenshot(region=(1000, 148, 936, 110))
img = img.resize((img.width * 2, img.height * 2))
img.save(r"D:\7tan\7tanAI\tabs2.png")

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
            xs = [wd.bounding_rect.x for wd in words]
            ys = [wd.bounding_rect.y for wd in words]
            x2 = max(wd.bounding_rect.x + wd.bounding_rect.width for wd in words)
            y2 = max(wd.bounding_rect.y + wd.bounding_rect.height for wd in words)
            x, y = int(min(xs)), int(min(ys))
            wd, ht = int(x2 - x), int(y2 - y)
        else:
            x = y = wd = ht = 0
        # 还原原始坐标（2x缩放，起点1000,148）
        out.append((1000 + x//2, 148 + y//2, wd//2, ht//2, line.text))
    return out

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\tabs2.png"))
print("===== 搜索面板顶部（原始坐标） =====")
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
