# -*- coding: utf-8 -*-
"""最大化微信 -> 搜索'游戏推荐' -> 点文章tab -> OCR"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui, win32con, pyperclip

# 找微信窗口并最大化
def enum_all():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            out.append((hwnd, t))
    win32gui.EnumWindows(cb, None)
    return out

wx = None
for hwnd, t in enum_all():
    if '微信' in t:
        wx = hwnd
        break
if not wx:
    print('无微信窗口'); sys.exit(1)

win32gui.ShowWindow(wx, win32con.SW_MAXIMIZE)
time.sleep(0.5)
win32gui.SetForegroundWindow(wx)
time.sleep(0.8)
print('微信:', wx, win32gui.GetWindowRect(wx), '前台:', win32gui.GetWindowText(win32gui.GetForegroundWindow()))

# 搜索
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
time.sleep(3.5)

img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\s_ok1.png")
print('saved s_ok1.png')

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

items = asyncio.run(ocr_items(r"D:\7tan\7tanAI\s_ok1.png"))
print("===== 搜索结果页 =====")
for x, y, w, h, t in items:
    if x > 900 and 100 <= y < 1000:
        print(f"[{x},{y} {w}x{h}] {t}")
