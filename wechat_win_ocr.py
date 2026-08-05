# -*- coding: utf-8 -*-
"""获取微信rect并截取窗口区域OCR"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

hwnd = 66948
rect = win32gui.GetWindowRect(hwnd)
print('微信 rect:', rect, '宽:', rect[2]-rect[0], '高:', rect[3]-rect[1])
print('前台:', win32gui.GetForegroundWindow(), win32gui.GetWindowText(win32gui.GetForegroundWindow()))

# 如果窗口不在前台或不是最大化，先处理
if win32gui.GetForegroundWindow() != hwnd:
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    time.sleep(0.5)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    rect = win32gui.GetWindowRect(hwnd)
    print('重新最大化后 rect:', rect)

# 截取微信窗口区域（窗口内容起点约 rect+8）
x0, y0 = rect[0] + 8, rect[1] + 8
w, h = rect[2] - rect[0] - 16, rect[3] - rect[1] - 16
img = pyautogui.screenshot(region=(max(x0,0), max(y0,0), w, h))
img.save(r"D:\7tan\7tanAI\wechat_win.png")
print('窗口截图:', img.size)

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

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\wechat_win.png"))
print("===== 微信窗口内容 (窗口内坐标) =====")
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
