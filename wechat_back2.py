# -*- coding: utf-8 -*-
"""点击左上角返回按钮，回到微信主界面"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui

HWND = 66948
win32gui.SetForegroundWindow(HWND)
time.sleep(0.6)

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

# 尝试几个返回按钮位置
for pos in [(40, 40), (40, 60), (80, 40), (60, 50), (30, 30)]:
    pyautogui.click(pos[0], pos[1])
    time.sleep(1.0)
    items = asyncio.run(ocr_items(snap('back_try')))
    # 检查是否出现聊天列表（x<300 有内容）
    left_has = any(x < 300 and y > 100 and y < 900 for x, y, w, h, t in items)
    has_wuhu = any('wuhu' in t or '动画' in t for x, y, w, h, t in items if x > 1000)
    print(f"点击{pos}: 左侧有内容={left_has}, 还在文章页={has_wuhu}")
    if left_has and not has_wuhu:
        print('已返回主界面！')
        break
    # 尝试 Esc
    pyautogui.press('esc')
    time.sleep(0.8)

print("===== 最终界面 =====")
items = asyncio.run(ocr_items(snap('final_state')))
for x, y, w, h, t in items:
    if 100 <= y < 1000:
        print(f"[{x},{y} {w}x{h}] {t}")
