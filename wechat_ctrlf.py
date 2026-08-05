# -*- coding: utf-8 -*-
"""按 Ctrl+F 打开微信搜索，OCR验证"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui

win32gui.SetForegroundWindow(66948)
time.sleep(0.6)
pyautogui.hotkey('ctrl', 'f')
time.sleep(1.5)

img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\ctrl_f.png")
print('saved ctrl_f.png')

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_items(path):
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
        out.append((x, y, wd, ht, line.text))
    return out

items = asyncio.run(ocr_items(r"D:\7tan\7tanAI\ctrl_f.png"))
print("===== Ctrl+F 后界面 =====")
for x, y, w, h, t in items:
    if x > 500 and 50 <= y < 1000:
        print(f"[{x},{y} {w}x{h}] {t}")
