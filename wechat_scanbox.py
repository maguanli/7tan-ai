# -*- coding: utf-8 -*-
"""扫描顶部搜索框位置：逐个点击候选坐标，OCR检测输入框是否出现"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui

win32gui.SetForegroundWindow(66948)
time.sleep(0.5)

def snap_top():
    img = pyautogui.screenshot(region=(0, 0, 900, 130))
    img.save(r"D:\7tan\7tanAI\scan_top_try.png")

async def ocr_top():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    file = await StorageFile.get_file_from_path_async(r"D:\7tan\7tanAI\scan_top_try.png")
    stream = await file.open_async(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    result = await engine.recognize_async(bitmap)
    return [line.text for line in result.lines]

# 候选坐标（x, y）
candidates = [
    (100, 40), (150, 40), (200, 40), (250, 40), (300, 40), (350, 40),
    (100, 50), (150, 50), (200, 50), (250, 50), (300, 50), (350, 50),
    (100, 60), (150, 60), (200, 60), (250, 60), (300, 60),
    (180, 30), (180, 70), (50, 40), (50, 50),
]

# 先截一张基准
snap_top()
base = set(asyncio.run(ocr_top()))
print('基准顶部文字:', base)

for x, y in candidates:
    pyautogui.click(x, y)
    time.sleep(0.9)
    snap_top()
    texts = asyncio.run(ocr_top())
    joined = '|'.join(texts)
    new = [t for t in texts if t not in base]
    if new:
        print(f'坐标({x},{y}) 出现新文字: {new}')
    # 检测输入框特征
    if '搜索' in joined or '游戏' in joined or '输入' in joined:
        print(f'>>> 疑似搜索框: ({x},{y}) -> {texts}')
        break
