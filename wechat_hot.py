# -*- coding: utf-8 -*-
"""点击'最热'排序，抓取高热度文章清单"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pygetwindow as gw

wins = gw.getWindowsWithTitle('微信')
if wins:
    wins[0].activate()
    time.sleep(0.5)

# 先回到搜索结果（按 Esc 或点击搜索框）: 当前可能停在文章详情，先点击文章区域外返回
# 直接点击"最热"排序按钮位置（搜索结果页 x≈1120,y≈219）
# 但当前可能停留在文章详情页，先按 ESC 返回
pyautogui.press('esc')
time.sleep(1.0)
pyautogui.click(1120, 219)
time.sleep(3.0)

img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\hot_articles.png")
print("saved hot_articles.png")

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
        out.append(f"[{x},{y} {wd}x{ht}] {line.text}")
    return "\n".join(out)

text = asyncio.run(ocr_file(r"D:\7tan\7tanAI\hot_articles.png"))
print("=====HOT ARTICLES OCR=====")
print(text)
print("=====END=====")
