# -*- coding: utf-8 -*-
"""综合流程：清理窗口 -> 微信最大化 -> 搜索'游戏推荐' -> 文章tab -> 最热 -> OCR"""
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

# ===== 1. 清理窗口 =====
wechat_hwnd = None
for hwnd, t, cls in enum_all():
    if '微信' in t:
        wechat_hwnd = hwnd
        continue
    if cls in ('Progman', 'Shell_TrayWnd', 'WorkerW'):
        continue
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    except Exception:
        pass

time.sleep(0.8)

# ===== 2. 微信最大化置顶 =====
if wechat_hwnd:
    win32gui.ShowWindow(wechat_hwnd, win32con.SW_MAXIMIZE)
    time.sleep(0.5)
    win32gui.SetForegroundWindow(wechat_hwnd)
    print('微信 rect:', win32gui.GetWindowRect(wechat_hwnd))
time.sleep(1.0)

# ===== 3. 搜索 =====
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

# ===== 4. 点"文章" =====
items = asyncio.run(ocr_items(snap('f1')))
pos = find(items, '文章')
print('文章tab:', pos)
if pos:
    pyautogui.click(pos[0], pos[1])
    time.sleep(2.5)

# ===== 5. 点"最热" =====
items = asyncio.run(ocr_items(snap('f2')))
pos = find(items, '最热')
print('最热:', pos)
if pos:
    pyautogui.click(pos[0], pos[1])
    time.sleep(3.5)

# ===== 6. 输出 =====
items = asyncio.run(ocr_items(snap('f3')))
print("===== 文章列表 =====")
for x, y, w, h, t in items:
    if x > 950 and 130 <= y < 950:
        print(f"[{x},{y} {w}x{h}] {t}")
