# -*- coding: utf-8 -*-
"""点击搜索结果第一条，打开聊天窗口并确认"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

def find_wechat():
    wins = []
    def cb(h, out):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t and ('微信' in t or 'Weixin' in t or 'WeChat' in t):
                out.append((h, t))
    win32gui.EnumWindows(cb, wins)
    return wins

wins = find_wechat()
if not wins:
    print('未找到微信窗口'); sys.exit(1)
hwnd = wins[0][0]
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.3)
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.8)

# 点击搜索结果第一条 "7坛游戏社区" (OCR坐标 137,131)
x, y = 137, 131
pyautogui.click(x, y)
time.sleep(2.5)

# 截图确认聊天窗口
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_chat.png")
print('已截图')

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

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_chat.png"))
print("===== 聊天窗口画面 =====")
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
