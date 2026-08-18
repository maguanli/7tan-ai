# -*- coding: utf-8 -*-
"""点击文章Tab(1755,164) → 定位并点击最热 → 读取文章列表"""
import ctypes, sys, io, time
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

def ocr(img, scale=4, region=None):
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
    return [(l.text, l.words[0].bounding_rect if l.words else None) for l in res.lines if l.text.strip()]

activate_wx()
time.sleep(0.3)

# 1. 点击文章 Tab
pyautogui.click(1755, 164)
time.sleep(2.5)
print("[CLICK] 文章Tab (1755,164)")

img = grab()
img.save(r"D:\7tan\7tanAI\data\screenshots\article_tab3.png")

# 2. 精确定位排序行（找最热）
print("=== 排序行 OCR (1450,205)-(1936,260) ===")
sort_items = []
for t, r in ocr(img, 4, (1450, 205, 1936, 260)):
    x = int(r.x/4) + 1450
    y = int(r.y/4) + 205
    w = int(r.width/4)
    cx = x + w // 2
    sort_items.append((t, cx, y))
    print(f"  '{t}' 中心x={cx} y={y}")

# 3. 找"最热"并点击
hot_item = None
for t, cx, y in sort_items:
    if "最热" in t.replace(" ", ""):
        hot_item = (cx, y)
        break

if hot_item:
    hx, hy = WL + hot_item[0], WT + hot_item[1] + 6
    print(f"\n[CLICK] 最热 ({hx},{hy})")
    pyautogui.click(hx, hy)
    time.sleep(2.5)

    # 4. 读取最热文章列表
    img2 = grab()
    img2.save(r"D:\7tan\7tanAI\data\screenshots\hot_articles.png")
    print("\n=== 最热文章列表 OCR ===")
    for t, r in ocr(img2, 2, (1460, 240, 1936, 900)):
        pos = f"({int(r.x/2)+1460},{int(r.y/2)+240})" if r else ""
        print(f"  {t} {pos}")
else:
    print("未找到'最热'选项！")
    # 输出列表现状
    print("\n=== 当前列表 OCR ===")
    for t, r in ocr(img, 2, (1460, 240, 1936, 900)):
        pos = f"({int(r.x/2)+1460},{int(r.y/2)+240})" if r else ""
        print(f"  {t} {pos}")
