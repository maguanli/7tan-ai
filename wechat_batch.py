# -*- coding: utf-8 -*-
"""批量搜索关键词，从结果卡片筛选阅读量(万/10万+)"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui, pyperclip

WX = 133410

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

def do_search(key):
    win32gui.SetForegroundWindow(WX)
    time.sleep(0.4)
    pyautogui.click(180, 48)
    time.sleep(1.0)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.press('delete')
    time.sleep(0.3)
    pyperclip.copy(key)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(3.5)
    return asyncio.run(ocr_items(snap('kw_' + key[:6])))

keywords = ['必玩的游戏', '游戏排行榜', '单机手游推荐', '耐玩的游戏', '游戏 攻略']

for kw in keywords:
    try:
        items = do_search(kw)
        print(f'\n===== 关键词: {kw} =====')
        # 找阅读量/万 标记
        for x, y, w, h, t in items:
            if x > 900 and 100 <= y < 1000:
                # 显示含'万'或'10万'或'阅读'的行（可能是阅读量）
                if ('万' in t and ('10' in t or '2' in t or '5' in t or '8' in t or '3' in t)) or '阅读' in t:
                    print(f"[阅读标记 {x},{y}] {t}")
        # 输出所有游戏相关标题行
        for x, y, w, h, t in items:
            if x > 900 and 150 <= y < 950 and ('游戏' in t or '手游' in t) and len(t) > 8:
                print(f"  [标题 {x},{y}] {t}")
    except Exception as e:
        print(f'关键词 {kw} 出错: {e}')
