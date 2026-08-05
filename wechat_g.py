# -*- coding: utf-8 -*-
"""当前搜索面板按回车触发搜索 -> 点'文章' -> 点'最热' -> OCR"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui, pyperclip

HWND = 66948

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

def find(items, target, xmin=900, xmax=1936, ymin=100, ymax=320):
    for x, y, w, h, t in items:
        if target in t and xmin <= x <= xmax and ymin <= y <= ymax:
            return (x + w // 2, y + h // 2)
    return None

win32gui.SetForegroundWindow(HWND)
time.sleep(0.5)

# 点输入框确保聚焦，再回车
pyautogui.click(1022, 224)
time.sleep(0.8)
pyautogui.press('enter')
time.sleep(3.0)

# 点"文章" tab
items = asyncio.run(ocr_items(snap('g1')))
pos = find(items, '文章')
print('文章tab:', pos)
if pos:
    pyautogui.click(pos[0], pos[1])
    time.sleep(2.5)
else:
    print('无文章tab，顶部：')
    for x, y, w, h, t in items:
        if y < 320 and x > 900:
            print(f"[{x},{y}] {t}")

# 点"最热"
items = asyncio.run(ocr_items(snap('g2')))
pos = find(items, '最热')
print('最热:', pos)
if pos:
    pyautogui.click(pos[0], pos[1])
    time.sleep(3.5)

# 输出
items = asyncio.run(ocr_items(snap('g3')))
print("===== 文章列表 =====")
for x, y, w, h, t in items:
    if x > 950 and 130 <= y < 950:
        print(f"[{x},{y} {w}x{h}] {t}")
