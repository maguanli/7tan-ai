# -*- coding: utf-8 -*-
"""抢占式：移走7Tan -> 微信最大化 -> 搜索'游戏推荐' -> 点文章tab -> 截图"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui, win32con, pyperclip

def enum_all():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            out.append((hwnd, t, cls))
    win32gui.EnumWindows(cb, None)
    return out

# 1. 移走 7Tan（restore后MoveWindow到屏外）
moved = []
for hwnd, t, cls in enum_all():
    if '7Tan' in t:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            rect = win32gui.GetWindowRect(hwnd)
            win32gui.MoveWindow(hwnd, -12000, -12000, rect[2]-rect[0], rect[3]-rect[1], True)
            moved.append((hwnd, rect))
            print('7Tan移走:', t, hwnd)
        except Exception as e:
            print('7Tan移走失败', e)

# 2. 微信最大化置顶
wechat = None
for hwnd, t, cls in enum_all():
    if '微信' in t:
        wechat = hwnd
        break
if wechat:
    win32gui.ShowWindow(wechat, win32con.SW_MAXIMIZE)
    time.sleep(0.4)
    win32gui.SetForegroundWindow(wechat)
    print('微信置顶:', wechat, win32gui.GetWindowRect(wechat))
time.sleep(0.8)

# 3. 快速操作序列
pyautogui.click(40, 40)          # 回主界面（若在文章页）
time.sleep(0.8)
pyautogui.click(180, 48)         # 搜索框
time.sleep(1.0)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.press('delete')
time.sleep(0.3)
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
pyautogui.press('enter')
time.sleep(3.0)
pyautogui.click(1200, 178)       # 文章tab（验证过位置）
time.sleep(3.0)

# 4. 截图OCR
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\final_list.png")
print('saved final_list.png')

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

items = asyncio.run(ocr_items(r"D:\7tan\7tanAI\final_list.png"))
print("===== 文章列表 =====")
for x, y, w, h, t in items:
    if x > 950 and 100 <= y < 1000:
        print(f"[{x},{y} {w}x{h}] {t}")

# 5. 恢复 7Tan
for hwnd, rect in moved:
    try:
        win32gui.MoveWindow(hwnd, rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1], True)
        print('7Tan已恢复')
    except Exception:
        pass
