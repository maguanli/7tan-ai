# -*- coding: utf-8 -*-
"""智能流程：打开搜索 -> OCR定位'文章' -> OCR定位'最热' -> 输出结果"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui, pyperclip

HWND = 66948

def fg():
    win32gui.SetForegroundWindow(HWND)
    time.sleep(0.5)

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

def find(items, target, xmin=950, xmax=1936, ymin=120, ymax=300):
    for x, y, w, h, t in items:
        if target in t and xmin <= x <= xmax and ymin <= y <= ymax:
            return (x + w // 2, y + h // 2)
    return None

def snap(name):
    img = pyautogui.screenshot()
    img.save(rf"D:\7tan\7tanAI\{name}.png")
    return rf"D:\7tan\7tanAI\{name}.png"

# 1. 打开搜索
fg()
pyautogui.click(180, 48)
time.sleep(1.2)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.press('delete')
time.sleep(0.4)
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.6)
pyautogui.press('enter')
time.sleep(3.0)

# 2. 找并点'文章'
items = asyncio.run(ocr_items(snap('step1')))
pos = find(items, '文章')
print('定位 文章:', pos)
if pos:
    pyautogui.click(pos[0], pos[1])
    time.sleep(2.5)
else:
    print('未找到文章tab，输出顶部:')
    for it in items:
        if it[1] < 300 and it[0] > 900:
            print(it)

# 3. 找并点'最热'
items = asyncio.run(ocr_items(snap('step2')))
pos = find(items, '最热')
print('定位 最热:', pos)
if pos:
    pyautogui.click(pos[0], pos[1])
    time.sleep(3.5)

# 4. 输出结果
items = asyncio.run(ocr_items(snap('step3')))
print("===== 结果列表 =====")
for x, y, w, h, t in items:
    if x > 950 and 140 <= y < 900:
        print(f"[{x},{y} {w}x{h}] {t}")
