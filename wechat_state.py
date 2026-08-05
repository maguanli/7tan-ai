# -*- coding: utf-8 -*-
"""稳定重现：清空搜索框 -> 搜索'游戏推荐' -> 确认界面"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pygetwindow as gw, pyperclip

wins = gw.getWindowsWithTitle('微信')
if wins:
    wins[0].activate()
    time.sleep(0.8)

# 点击搜索框
pyautogui.click(180, 48)
time.sleep(1.2)

# 全选清空
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.press('delete')
time.sleep(0.5)

# 粘贴关键词
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.8)

# 截图看输入状态
img = pyautogui.screenshot(region=(1000, 100, 936, 180))
img = img.resize((img.width * 2, img.height * 2))
img.save(r"D:\7tan\7tanAI\state_input.png")
print("saved state_input.png")

pyautogui.press('enter')
time.sleep(3.0)

img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\state_after_enter.png")
print("saved state_after_enter.png")

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

print("=====STATE AFTER ENTER=====")
text = asyncio.run(ocr_file(r"D:\7tan\7tanAI\state_after_enter.png"))
print(text)
print("=====END=====")
