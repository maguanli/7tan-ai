# -*- coding: utf-8 -*-
"""关闭开始菜单 -> 微信置顶 -> 搜索'游戏推荐' -> 确认tab行"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui, win32con, pyperclip

# 1. 按 ESC 关闭开始菜单
pyautogui.press('esc')
time.sleep(0.8)

# 2. 微信置顶
def find_windows(title_part):
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if title_part in t:
                out.append(hwnd)
    win32gui.EnumWindows(cb, None)
    return out

for hwnd in find_windows('微信'):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    break
time.sleep(0.8)

# 3. 点击搜索框
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
img.save(r"D:\7tan\7tanAI\s2_result.png")
print('saved s2_result.png')

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
        out.append((x, y, wd, ht, line.text))
    return out

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\s2_result.png"))
print("===== 顶部/右侧区域(搜索面板) =====")
for x, y, w, h, t in items:
    if y < 300 and x > 800:
        print(f"[{x},{y} {w}x{h}] {t}")
print("===== 中部区域 =====")
for x, y, w, h, t in items:
    if 300 <= y < 700 and x > 800:
        print(f"[{x},{y} {w}x{h}] {t}")
