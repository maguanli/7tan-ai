# -*- coding: utf-8 -*-
"""滚动最热文章列表，抓取全部标题"""
import ctypes, sys, io, time, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 198562
WL, WT = -8, -8

def activate_wx():
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.4)

def grab(box=(WL, WT, 1936, 1056)):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def ocr(img, scale=2, region=None):
    if region:
        img = img.crop(region)
    img2 = img.resize((img.width*scale, img.height*scale), Image.LANCZOS)
    buf = io.BytesIO(); img2.save(buf, format="PNG"); data = buf.getvalue()
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
    w.write_bytes(data)
    if hasattr(w, "store"): w.store()
    else: w.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bmp = decoder.get_software_bitmap_async().get()
    res = engine.recognize_async(bmp).get()
    return [l.text for l in res.lines if l.text.strip()]

activate_wx()
time.sleep(0.3)
pyautogui.moveTo(1750, 500)
time.sleep(0.3)

titles = []
seen = set()
for i in range(10):
    img = grab()
    texts = ocr(img, 2, (1460, 240, 1936, 1056))
    for t in texts:
        t_clean = t.replace(" ", "")
        # 标题特征：较长 或 包含游戏词
        if len(t_clean) >= 10 and not re.search(r"手讠姬|什么值得买|游戏基米|POP|2025|2024|2023|2022|天前|个月前|小时前|丷", t_clean):
            key = t_clean[:18]
            if key not in seen:
                seen.add(key)
                titles.append(t)
    pyautogui.scroll(-4)
    time.sleep(0.7)

print(f"\n=== 最热文章标题汇总（{len(titles)} 条）===")
for t in titles:
    print(" ", t.replace(" ", ""))
