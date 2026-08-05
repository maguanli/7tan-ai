# -*- coding: utf-8 -*-
"""验证搜索结果的游戏文章阅读量：返回->点卡片->滚到底->OCR"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui

WX = 133410

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

def find(items, targets):
    """找包含任一目标文字的行，返回第一个"""
    for x, y, w, h, t in items:
        for tg in targets:
            if tg in t:
                return (x, y, w, h, t)
    return None

win32gui.SetForegroundWindow(WX)
time.sleep(0.5)

# 返回搜索结果（点左上角返回按钮）
pyautogui.click(40, 40)
time.sleep(2.0)

# 点击"手游推荐：8月适合长玩的爆款手游排行榜 TOP6"（约在结果列表中部）
pyautogui.click(1050, 835)
time.sleep(4.0)
for _ in range(6):
    pyautogui.press('end')
    time.sleep(0.7)

items = asyncio.run(ocr_items(snap('top6_1')))
print("===== 文章1 阅读量行 =====")
for x, y, w, h, t in items:
    if ('阅' in t) or ('万' in t):
        print(f"[{x},{y} {w}x{h}] {t}")
print("--- 底部区域 ---")
for x, y, w, h, t in items:
    if x > 900 and y > 700:
        print(f"[{x},{y} {w}x{h}] {t}")
