# -*- coding: utf-8 -*-
"""动态查找微信窗口句柄并OCR识别状态"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

# 动态查找微信窗口（标题含 微信/Weixin/WeChat，且可见）
def find_wechat_windows():
    wins = []
    def cb(h, out):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t and ('微信' in t or 'Weixin' in t or 'WeChat' in t):
                out.append((h, t))
    win32gui.EnumWindows(cb, wins)
    return wins

wins = find_wechat_windows()
print('微信窗口列表:', wins)
if not wins:
    print('未找到微信窗口')
    sys.exit(1)

hwnd, title = wins[0]
print('使用窗口:', hwnd, title)

try:
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.3)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.8)
except Exception as e:
    print('激活失败:', e)

rect = win32gui.GetWindowRect(hwnd)
print('rect:', rect, '宽:', rect[2]-rect[0], '高:', rect[3]-rect[1])

x0, y0 = rect[0] + 8, rect[1] + 8
w, h = rect[2] - rect[0] - 16, rect[3] - rect[1] - 16
img = pyautogui.screenshot(region=(max(x0,0), max(y0,0), max(w,1), max(h,1)))
img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_win.png")
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

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_win.png"))
print("===== 微信窗口内容 (窗口内坐标) =====")
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")

text_all = ' '.join(t for _, _, _, _, t in items)
if '扫一扫' in text_all or '登录' in text_all or '二维码' in text_all or '扫码' in text_all:
    print(">> 状态: 需要扫码登录")
elif '聊天' in text_all or '通讯录' in text_all or '搜索' in text_all or '文件传输助手' in text_all:
    print(">> 状态: 已登录（主界面）")
else:
    print(">> 状态: 无法判断:", text_all[:100])
