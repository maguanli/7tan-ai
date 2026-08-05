# -*- coding: utf-8 -*-
"""滚动结果列表 -> OCR定位文章标题 -> 点击 -> 滚到底 -> 看阅读量"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui

HWND = 66948
win32gui.SetForegroundWindow(HWND)
time.sleep(0.6)

def snap(name):
    img = pyautogui.screenshot()
    img.save(rf"D:\7tan\7tanAI\{name}.png")
    return rf"D:\7tan\7tanAI\{name}.png"

async def ocr_items(path):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
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

# 在结果区滚动（鼠标悬停在列表上滚轮）
pyautogui.moveTo(1200, 500)
pyautogui.scroll(-8)
time.sleep(1.5)
pyautogui.scroll(-8)
time.sleep(1.5)

items = asyncio.run(ocr_items(snap('scrolled1')))
print("===== 滚动后结果 =====")
for x, y, w, h, t in items:
    if x > 950 and 130 <= y < 1000:
        print(f"[{x},{y} {w}x{h}] {t}")
