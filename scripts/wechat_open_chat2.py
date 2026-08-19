# -*- coding: utf-8 -*-
"""点击左侧列表群聊入口，确认窗口标题"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui
from PIL import Image

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
print('激活后窗口标题:', win32gui.GetWindowText(hwnd))

# 点击左侧聊天列表 "7游戏" 群 (126,813)
pyautogui.click(126, 813)
time.sleep(2.5)

print('点击后窗口标题:', win32gui.GetWindowText(hwnd))

# 全屏截图
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_chat2.png")

# 截取右侧聊天区域顶部（标题栏区域 y 150-260, x 400-1400）放大2x 提高OCR
crop = img.crop((400, 140, 1400, 280)).resize((2000, 280), Image.LANCZOS)
crop.save(r"D:\7tan\7tanAI\data\screenshots\wechat_title_zoom.png")
print('顶部放大图已存')

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

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_title_zoom.png"))
print("===== 右侧聊天区顶部标题 (放大OCR) =====")
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
