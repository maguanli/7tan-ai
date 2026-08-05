# -*- coding: utf-8 -*-
"""循环尝试返回主界面，直到检测到聊天列表"""
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

win32gui.SetForegroundWindow(WX)
time.sleep(0.5)

# 尝试多种返回方式
attempts = [(40, 40), (40, 30), (60, 40), (20, 40), (40, 50), (80, 40), (100, 40), (30, 35)]
for i, pos in enumerate(attempts):
    pyautogui.click(pos[0], pos[1])
    time.sleep(1.5)
    items = asyncio.run(ocr_items(snap(f'back_try{i}')))
    # 检测聊天列表（x<300 有聊天名如'服务号'/'微信支付'）
    chat = any(x < 300 and 200 < y < 900 and any(k in t for k in ['微', '号', '支付', '服务', '抖音']) for x, y, w, h, t in items)
    article = any(x > 900 and ('阅读' in t or '写留言' in t or '作者' in t) for x, y, w, h, t in items)
    print(f'尝试{pos}: 聊天特征={chat} 文章特征={article}')
    if chat and not article:
        print('>>> 已回到主界面')
        break
    # 尝试 ESC
    pyautogui.press('esc')
    time.sleep(0.8)
else:
    print('未能返回主界面，最终状态:')
    items = asyncio.run(ocr_items(snap('final_back')))
    for x, y, w, h, t in items:
        if 100 <= y < 1000:
            print(f"[{x},{y} {w}x{h}] {t}")
